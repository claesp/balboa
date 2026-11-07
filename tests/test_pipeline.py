import io
import json
from pathlib import Path
import tarfile
import tempfile
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

from balboa.cli import checksum_entry
from balboa.render import render_text, valid_site
from balboa.vm import extract_evidence, inspect_system, observe
from balboa.storage import layout
from guest.result_gate import assess, NS

PROFILE = "xccdf_org.ssgproject.content_profile_cis"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        # An Ed25519 wire-format blob. It carries no private key.
        import base64
        blob = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes(range(32))
        self.site = {"hostname": "host.example.test", "username": "operator",
                     "password_hash": "$6$salt$" + "a" * 86,
                     "bootloader_password_hash": "grub.pbkdf2.sha512.100000." + "A" * 128 + "." + "B" * 128,
                     "ssh_public_key": "ssh-ed25519 " + base64.b64encode(blob).decode(),
                     "timezone": "UTC", "keyboard": "us", "language": "en_US.UTF-8"}

    def tearDown(self):
        self.temp.cleanup()

    def report(self, values, profile=PROFILE):
        root = ET.Element(f'{{{NS["x"]}}}Benchmark')
        result = ET.SubElement(root, f'{{{NS["x"]}}}TestResult')
        ET.SubElement(result, f'{{{NS["x"]}}}profile', idref=profile)
        for i, value in enumerate(values):
            rule = ET.SubElement(result, f'{{{NS["x"]}}}rule-result', idref=f"rule_{i}")
            ET.SubElement(rule, f'{{{NS["x"]}}}result').text = value
        path = self.root / "results.xml"
        ET.ElementTree(root).write(path)
        return path

    def test_signed_checksum_rejects_ambiguous_entries(self):
        entry = f'SHA256 (image.iso) = {"a" * 64}\n'
        self.assertEqual(checksum_entry(entry, "image.iso"), "a" * 64)
        for text in (entry * 2, entry.replace("image.iso", "other.iso"), ""):
            with self.subTest(text=text), self.assertRaises(ValueError):
                checksum_entry(text, "image.iso")

    def test_site_rejects_kickstart_and_shell_injection(self):
        for field in self.site:
            with self.subTest(field=field), self.assertRaises(ValueError):
                valid_site({**self.site, field: self.site[field] + '\n%post\ntouch /tmp/injected'})
        with self.assertRaises(ValueError):
            valid_site({**self.site, "ssh_public_key": "ssh-ed25519 AAAA"})
        with self.assertRaises(ValueError):
            valid_site({**self.site, "username": "root"})

    def test_production_requires_disk_and_never_embeds_encryption_secret(self):
        with self.assertRaises(ValueError):
            render_text("server", self.site, None, "boot")
        with self.assertRaises(ValueError):
            render_text("server", self.site, "sda,sdb", "boot")
        text, _ = render_text("server", self.site, "disk/by-id/nvme-Example_123", "boot")
        self.assertIn("--only-use=disk/by-id/nvme-Example_123", text)
        self.assertIn("--encrypted --luks-version=luks2\n", text)
        self.assertNotIn("--passphrase", text)
        self.assertNotIn("@@", text)

    def test_lab_requires_isolated_disk_and_generated_secret(self):
        for disk, secret in (("sda", "a" * 40), ("vda", None), ("vda", 'x"\n%post')):
            with self.subTest(disk=disk), self.assertRaises(ValueError):
                render_text("server", self.site, disk, "boot", True, secret)
        text, _ = render_text("server", self.site, "vda", "boot", True, "a" * 40)
        self.assertIn('--passphrase="' + "a" * 40 + '"', text)
        self.assertIn("cmdline\n", text)

    def test_flavors_select_correct_profile_and_source(self):
        for flavor in ("server", "workstation", "laptop"):
            for kind in ("boot", "dvd"):
                with self.subTest(flavor=flavor, kind=kind):
                    text, definition = render_text(flavor, self.site, "vda", kind)
                    expected = PROFILE if flavor == "server" else PROFILE + "_workstation_l2"
                    self.assertEqual(definition["profile"], expected)
                    self.assertEqual("\ncdrom\n" in text, kind == "dvd")
                    self.assertEqual("\nNetworkManager-wifi\n" in text, flavor == "laptop")
                    self.assertIn("@core --nodefaults", text)
                    self.assertNotIn("@^", text)
                    self.assertIn("--exclude-weakdeps", text)
                    self.assertNotIn("--grow", text)

    def test_storage_has_fixed_sizes_and_identical_test_mounts(self):
        production = layout()
        lab = layout(lab=True)
        self.assertEqual(production["disk_bytes"], 128_000_000_000)
        self.assertEqual(lab["disk_bytes"], 32_000_000_000)
        self.assertEqual([v["mount"] for v in production["volumes"]], [v["mount"] for v in lab["volumes"]])
        for plan in (production, lab, layout(24), layout(256)):
            self.assertEqual(sum(v["size_mib"] for v in plan["volumes"]), plan["pv_mib"] - plan["lvm_reserve_mib"])
            for volume in plan["volumes"]:
                self.assertGreaterEqual(volume["size_mib"], volume["minimum_mib"])
                if volume["mount"] in ("/tmp", "/var/tmp", "/var/log", "/var/log/audit"):
                    self.assertEqual(set(volume["options"].split(",")), {"nodev", "nosuid", "noexec"})
        for size in (True, 0, 16, -1, "128", 20000):
            with self.subTest(size=size), self.assertRaises(ValueError):
                layout(size)

    def test_gate_rejects_wrong_platform_empty_and_small_reports(self):
        for values in ([], ["notapplicable"] * 400, ["pass"] * 99):
            with self.subTest(values=len(values)), self.assertRaises(ValueError):
                assess(self.report(values), PROFILE)
        with self.assertRaises(ValueError):
            assess(self.report(["pass"] * 100, PROFILE + "_server_l1"), PROFILE)

    def test_gate_blocks_every_unresolved_result(self):
        for value in ("fail", "error", "unknown", "notchecked", "fixed"):
            with self.subTest(value=value):
                summary = assess(self.report(["pass"] * 100 + [value]), PROFILE)
                self.assertFalse(summary["passed"])
                self.assertEqual(summary["findings"], ["rule_100"])
        self.assertTrue(assess(self.report(["pass"] * 100 + ["notapplicable"] * 10), PROFILE)["passed"])

    def test_gate_rejects_duplicate_rule_ids_and_unknown_status(self):
        path = self.report(["pass"] * 100)
        tree = ET.parse(path)
        rules = tree.findall(".//x:rule-result", NS)
        rules[-1].set("idref", rules[0].get("idref"))
        tree.write(path)
        with self.assertRaises(ValueError):
            assess(path, PROFILE)
        with self.assertRaises(ValueError):
            assess(self.report(["pass"] * 100 + ["surprise"]), PROFILE)

    def archive(self, name, kind=tarfile.REGTYPE):
        path = self.root / "evidence.tar.gz"
        with tarfile.open(path, "w:gz") as stream:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.linkname = "/etc/passwd" if kind == tarfile.SYMTYPE else ""
            member.size = 4 if kind == tarfile.REGTYPE else 0
            stream.addfile(member, io.BytesIO(b"test") if member.size else None)
        return path

    def test_guest_archive_cannot_escape_or_create_links(self):
        for name, kind in (("../outside", tarfile.REGTYPE), ("/tmp/outside", tarfile.REGTYPE),
                           ("other/data", tarfile.REGTYPE), ("evidence/link", tarfile.SYMTYPE)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                extract_evidence(self.archive(name, kind), self.root / "collected")
        self.assertFalse((self.root / "collected").exists())

    def test_guest_archive_extracts_only_under_target(self):
        extract_evidence(self.archive("evidence/summary.json"), self.root / "collected")
        self.assertEqual((self.root / "collected/evidence/summary.json").read_bytes(), b"test")

    def test_vm_unlock_waits_for_the_encryption_prompt(self):
        program = 'import sys; print("Please enter passphrase for disk:", flush=True); sys.exit(0 if sys.stdin.readline() == "disposable\\n" else 9)'
        observe([sys.executable, "-c", program], self.root / "serial.log", 10, "disposable")
        self.assertNotIn("disposable", (self.root / "serial.log").read_text())

    def test_vm_rejects_an_installer_failure(self):
        program = 'print("Non interactive installation failed: missing package", flush=True)'
        with self.assertRaises(ValueError):
            observe([sys.executable, "-c", program], self.root / "serial.log", 10, None)

    def system_evidence(self):
        plan = layout(lab=True)
        mounts = []
        for volume in plan["volumes"]:
            if volume["mount"] != "swap":
                mounts.append(f'{volume["mount"]} /dev/mapper/system-{volume["name"]} xfs rw,{volume["options"]}')
        (self.root / "mounts.txt").write_text("\n".join(mounts))
        (self.root / "packages.txt").write_text("openssh-server-9.9p1-1.el10.x86_64\n")
        (self.root / "selinux.txt").write_text("Enforcing\n")
        (self.root / "storage.txt").write_text("vda\nluks-test crypt\nsystem-root lvm\n")
        return {"flavor": "server", "storage": plan}, {"exclude": ["bluez", "NetworkManager-wifi"]}

    def test_guest_evidence_rejects_unrestricted_temporary_mounts(self):
        manifest, definition = self.system_evidence()
        inspect_system(manifest, self.root, definition)
        text = (self.root / "mounts.txt").read_text().replace("nodev,nosuid,noexec", "nodev,nosuid", 1)
        (self.root / "mounts.txt").write_text(text)
        with self.assertRaises(ValueError):
            inspect_system(manifest, self.root, definition)

    def test_guest_evidence_rejects_server_hardware_packages(self):
        manifest, definition = self.system_evidence()
        with (self.root / "packages.txt").open("a") as stream:
            stream.write("NetworkManager-wifi-1.56.0-1.el10.x86_64\n")
        with self.assertRaises(ValueError):
            inspect_system(manifest, self.root, definition)

    def test_first_boot_retains_findings_then_rejects_assessment(self):
        # Exercise the real service scripts without changing the host system.
        import os
        repository = Path(__file__).resolve().parent.parent
        guest = self.root / "guest"
        guest.mkdir()
        state = self.root / "state"
        aide = self.root / "aide"
        aide.mkdir()
        content = self.root / "content"
        content.mkdir()
        (content / "ssg-rl10-ds.xml").touch()
        config = self.root / "image.conf"
        config.write_text(f"PROFILE={PROFILE}\nLAB=no\nFLAVOR=workstation\n")
        replacements = {"/etc/balboa/image.conf": str(config), "/var/lib/balboa": str(state),
                        "/usr/local/libexec/balboa": str(guest), "/var/lib/aide": str(aide),
                        "/usr/share/xml/scap/ssg/content": str(content)}
        for name in ("harden.sh", "audit.sh", "failure.sh", "result_gate.py"):
            text = (repository / "guest" / name).read_text()
            for old, new in replacements.items():
                text = text.replace(old, new)
            (guest / name).write_text(text)
        fixture = self.report(["pass"] * 100 + ["fail"])
        programs = self.root / "bin"
        programs.mkdir()
        stubs = {
            "oscap": f'''#!/usr/bin/python3
import shutil, sys
if sys.argv[1] == "info":
    print("{PROFILE}:CIS Level 2")
    sys.exit(0)
for flag in ("--results", "--results-arf", "--report"):
    shutil.copyfile("{fixture}", sys.argv[sys.argv.index(flag) + 1])
sys.exit(2)
''',
            "aide": f"#!/bin/sh\ntouch {aide}/aide.db.new.gz\n",
            "rpm": "#!/bin/sh\nprintf 'fixture-package\\n'\n",
            "systemctl": "#!/bin/sh\nexit 0\n",
        }
        for name, text in stubs.items():
            (programs / name).write_text(text)
            (programs / name).chmod(0o755)
        env = {**os.environ, "PATH": f"{programs}:{os.environ['PATH']}"}
        hardening = subprocess.run(["bash", str(guest / "harden.sh")], env=env)
        self.assertEqual(hardening.returncode, 0, (state / "evidence/harden.log").read_text())
        self.assertTrue((state / "remediated").exists())
        self.assertFalse(json.loads((state / "evidence/remediation-summary.json").read_text())["passed"])
        # The audit also calls system inspection tools, which are constrained here.
        for name in ("lsblk", "findmnt", "getenforce"):
            (programs / name).write_text("#!/bin/sh\nprintf 'fixture\\n'\n")
            (programs / name).chmod(0o755)
        assessment = subprocess.run(["bash", str(guest / "audit.sh")], env=env)
        self.assertNotEqual(assessment.returncode, 0)
        self.assertTrue((state / "assessed").exists())
        self.assertFalse((state / "assessment-passed").exists())
        self.assertEqual((state / "evidence/oscap-exit-status").read_text().strip(), "2")
        self.assertFalse(json.loads((state / "evidence/summary.json").read_text())["passed"])


if __name__ == "__main__":
    unittest.main()
