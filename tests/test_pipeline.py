import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

from balboa.cli import checksum_entry
from balboa.render import render_text, valid_site, read_site, render
from balboa.vm import decode_evidence, extract_evidence, inspect_system, observe
from balboa.storage import layout
from balboa.policy import EXCLUSIONS, tailoring
from guest.result_gate import assess, NS
from guest.native_checks import validate_fingerprints, validate_key_access

PROFILE = "xccdf_org.ssgproject.content_profile_cis"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        # An Ed25519 wire-format blob. It carries no private key.
        import base64
        blob = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes(range(32))
        self.site = {"hostname": "host.example.test", "username": "adminuser",
                     "password_hash": "$6$salt$" + "a" * 86,
                     "root_password_hash": "$6$rootsalt$" + "b" * 86,
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

    def test_native_trust_requires_the_pinned_key_and_rejects_unknown_keys(self):
        policy = {"key_fingerprint": "A" * 40, "key_fingerprints": ["A" * 40, "B" * 64]}
        validate_fingerprints({"A" * 40}, policy)
        validate_fingerprints({"A" * 40, "B" * 64}, policy)
        for observed in (set(), {"B" * 64}, {"A" * 40, "C" * 40}):
            with self.subTest(observed=observed), self.assertRaises(ValueError):
                validate_fingerprints(observed, policy)

    def test_site_rejects_kickstart_and_shell_injection(self):
        for field in self.site:
            with self.subTest(field=field), self.assertRaises(ValueError):
                valid_site({**self.site, field: self.site[field] + '\n%post\ntouch /tmp/injected'})
        with self.assertRaises(ValueError):
            valid_site({**self.site, "ssh_public_key": "ssh-ed25519 AAAA"})
        with self.assertRaises(ValueError):
            valid_site({**self.site, "username": "root"})
        with self.assertRaises(ValueError):
            valid_site({**self.site, "username": "operator"})

    def test_journal_private_key_rejects_insecure_access(self):
        from types import SimpleNamespace
        validate_key_access(SimpleNamespace(st_uid=0, st_gid=321, st_mode=0o100640), 321)
        for uid, gid, mode in ((1000,321,0o640),(0,999,0o640),(0,321,0o644),(0,321,0o660)):
            with self.subTest(uid=uid,gid=gid,mode=mode), self.assertRaises(ValueError):
                validate_key_access(SimpleNamespace(st_uid=uid, st_gid=gid, st_mode=mode), 321)

    def test_keyboard_rejects_language_codes_and_console_keymap_names(self):
        for keyboard in ("sv", "se-latin1", "not-a-layout"):
            with self.subTest(keyboard=keyboard), self.assertRaisesRegex(ValueError, "supported XKB layout"):
                valid_site({**self.site, "keyboard": keyboard})

    def test_swedish_xkb_layout_renders_for_every_flavor(self):
        for flavor in ("server", "workstation", "laptop"):
            with self.subTest(flavor=flavor):
                text, _ = render_text(flavor, {**self.site, "keyboard": "se"}, "vda", "dvd")
                self.assertIn("\nkeyboard --xlayouts=se\n", text)

    def test_required_root_and_optional_logging_configuration(self):
        site = {**self.site,
                "journal_upload": {"url": "https://logs.example.test:19532",
                                   "trusted_certificate_file": "/etc/pki/balboa/ca.pem",
                                   "client_certificate_file": "/etc/pki/balboa/client.pem",
                                   "client_key_file": "/etc/pki/balboa/client.key"}}
        valid_site(site)
        text, _ = render_text("server", site, "vda", "dvd")
        self.assertIn("rootpw --iscrypted " + self.site["root_password_hash"], text)
        self.assertIn("/etc/systemd/journal-upload.conf.d/60-balboa.conf", text)
        self.assertIn("install -d -m 0755 /etc/systemd/journal-upload.conf.d", text)
        self.assertIn("/etc/systemd/system/systemd-journal-upload.service.d/60-balboa-credentials.conf", text)
        with self.assertRaises(ValueError):
            valid_site({**site, "root_password_hash": "plaintext"})

    def test_site_requires_a_root_console_password(self):
        without_root = {k:v for k,v in self.site.items() if k != "root_password_hash"}
        for site in (without_root, {**self.site, "root_password_hash": ""}):
            with self.subTest(site=site), self.assertRaises(ValueError):
                valid_site(site)

    def test_flavors_accept_matching_root_and_administrator_digests(self):
        site = {**self.site, "root_password_hash": self.site["password_hash"]}
        valid_site(site)
        for flavor in ("server", "workstation", "laptop"):
            with self.subTest(flavor=flavor):
                text, _ = render_text(flavor, site, "vda", "dvd")
                self.assertIn("rootpw --iscrypted " + site["password_hash"], text)
                self.assertIn("--groups=wheel --iscrypted --password=" + site["password_hash"], text)

    def test_disposable_tls_never_enters_production_or_uses_other_paths(self):
        tls = {"ca.pem": "test CA", "client.pem": "test certificate", "client.key": "test private key"}
        with self.assertRaises(ValueError):
            render_text("server", self.site, "vda", "dvd", lab_tls=tls)
        with self.assertRaises(ValueError):
            render_text("server", self.site, "vda", "dvd", True, "a" * 40, lab_tls={"../../etc/passwd": "value"})
        text, _ = render_text("server", self.site, "vda", "dvd", True, "a" * 40, lab_tls=tls)
        self.assertIn("chmod 0600 /etc/pki/balboa/client.key", text)
        self.assertIn("chmod 0644 /etc/pki/balboa/ca.pem", text)
        self.assertIn("install -d -m 0755 /etc/pki/balboa", text)

    def test_logging_rejects_insecure_or_injected_values(self):
        for upload in ({"url": "http://logs.example.test"},
                       {"url": "https://user:password@logs.example.test"},
                       {"url": "https://logs.example.test\nURL=http://other"},
                       {"url": "https://logs.example.test", "client_key_file": "/etc/pki/key"},
                       {"url": "https://logs.example.test", "trusted_certificate_file": "/etc/pki/../shadow"}):
            with self.subTest(upload=upload), self.assertRaises(ValueError):
                valid_site({**self.site, "journal_upload": upload})

    def test_production_requires_disk_and_defaults_to_interactive_encryption(self):
        with self.assertRaises(ValueError):
            render_text("server", self.site, None, "dvd")
        with self.assertRaises(ValueError):
            render_text("server", self.site, "sda,sdb", "dvd")
        text, _ = render_text("server", self.site, "disk/by-id/nvme-Example_123", "dvd")
        self.assertIn("--only-use=disk/by-id/nvme-Example_123", text)
        self.assertIn("--encrypted --luks-version=luks2\n", text)
        self.assertNotIn("--passphrase", text)
        self.assertNotIn("@@", text)
        text, _ = render_text("server", {**self.site, "luks_passphrase": None}, "vda", "dvd")
        self.assertNotIn("--passphrase", text)

    def test_production_embeds_only_an_explicit_luks_passphrase(self):
        import shlex
        secret = "A test with '$` ! @@TOKEN@@ punctuation"
        for flavor in ("server", "workstation", "laptop"):
            with self.subTest(flavor=flavor):
                text, _ = render_text(flavor, {**self.site, "luks_passphrase": secret}, "nvme0n1", "dvd")
                line = next(line for line in text.splitlines() if line.startswith("part pv.01"))
                self.assertIn("--passphrase=" + secret, shlex.split(line))
                self.assertIn("--ondisk=nvme0n1", line)

    def test_site_json_preserves_passphrase_spaces_and_all_other_fields(self):
        site = {**self.site, "luks_passphrase": " a printable test passphrase "}
        path = self.root / "site.json"
        path.write_text(json.dumps(site))
        path.chmod(0o600)
        self.assertEqual(read_site(path), site)

    def test_site_with_luks_key_rejects_public_access_and_nonregular_files(self):
        import os
        path = self.root / "site.json"
        path.write_text(json.dumps({**self.site, "luks_passphrase": "a sufficiently long test passphrase"}))
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            read_site(path)
        path.chmod(0o600)
        link = self.root / "link"
        link.symlink_to(path)
        with self.assertRaises(OSError):
            read_site(link)
        fifo = self.root / "fifo"
        os.mkfifo(fifo, 0o600)
        with self.assertRaises(ValueError):
            read_site(fifo)

    def test_luks_passphrase_rejects_controls_without_exposing_its_contents(self):
        for secret in ("four", "long secret value\n%post\n", "a secret with a null\0", "a" * 129,
                       "REPLACE_WITH_A_PLAINTEXT_LUKS_PASSPHRASE"):
            with self.subTest(length=len(secret)), self.assertRaises(ValueError) as error:
                valid_site({**self.site, "luks_passphrase": secret})
            self.assertNotIn(secret, str(error.exception))

    def test_luks_accepts_five_characters_and_keeps_lab_secrets_long(self):
        import shlex
        for secret in ("test5", "a" * 128):
            text, _ = render_text("laptop", {**self.site, "luks_passphrase": secret}, "vda", "dvd")
            line = next(line for line in text.splitlines() if line.startswith("part pv.01"))
            self.assertIn("--passphrase=" + secret, shlex.split(line))
        with self.assertRaises(ValueError):
            render_text("laptop", self.site, "vda", "dvd", True, "test5")

    def test_boot_splash_defaults_opt_out_and_graphical_lab(self):
        for flavor in ("server", "workstation", "laptop"):
            for lab, enabled in ((False, True), (False, False), (True, False), (True, True)):
                site = {**self.site}
                if lab == enabled:
                    site["boot_splash"] = enabled
                text, _ = render_text(flavor, site, "vda", "dvd", lab,
                                      "a" * 40 if lab else None)
                boot = next(line for line in text.splitlines() if line.startswith("bootloader "))
                self.assertEqual("rhgb quiet" in boot, enabled)
                self.assertEqual("plymouth.ignore-serial-consoles" in boot, enabled)
                self.assertEqual("\nplymouth-theme-script\n" in text, enabled)
                self.assertEqual("\nplymouth-plugin-label\n" in text, enabled)
                self.assertEqual("\nfontconfig\n" in text, enabled)
                self.assertEqual(" > /usr/share/plymouth/themes/balboa/spinner.png\n" in text, enabled)
                self.assertEqual(" > /usr/share/plymouth/themes/balboa/entry.png\n" in text, enabled)
                self.assertIn("audit=1 audit_backlog_limit=8192", boot)
                if lab:
                    expected = ("console=ttyS0,115200n8 console=tty0" if enabled else
                                "console=tty0 console=ttyS0,115200n8")
                    self.assertIn(expected, boot)
                if not enabled:
                    self.assertIn("plymouth.enable=0", boot)

    def test_boot_splash_requires_a_boolean(self):
        for value in (None, 0, 1, "yes", []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                valid_site({**self.site, "boot_splash": value})

    def test_automated_vm_rejects_graphical_unlock_before_creating_storage(self):
        import hashlib
        from types import SimpleNamespace
        from balboa.vm import vm
        iso = self.root / "graphical.iso"
        iso.write_bytes(b"disposable ISO fixture")
        iso.with_suffix(".json").write_text(json.dumps({
            "iso_sha256": hashlib.sha256(iso.read_bytes()).hexdigest(),
            "lab": True, "boot_splash": True}))
        work = self.root / "vm"
        with self.assertRaisesRegex(ValueError, "start-qemu.py"):
            vm(SimpleNamespace(iso=iso, lab_secrets=None, workdir=work))
        self.assertFalse(work.exists())

    def test_branding_rejects_changed_source_assets(self):
        from unittest.mock import patch
        from balboa import branding
        corrupt = self.root / "unapproved-photo.jpg"
        corrupt.write_bytes(b"not the approved photo")
        with patch.object(branding, "PHOTO", corrupt), self.assertRaisesRegex(ValueError, "does not match"):
            branding.sources()

    def test_branding_rejects_controls_and_escapes_literal_text(self):
        from balboa import branding
        for value in (None, "", " ", "a" * 65, "text\n%post", 12):
            with self.subTest(value=value), self.assertRaises(ValueError):
                valid_site({**self.site, "branding_text": value})
        label = '<logo> & "example"'
        for name in branding.SIZES:
            with self.subTest(name=name):
                root = ET.fromstring(branding.vector(label, name))
                text, = root
                self.assertTrue(text.tag.endswith("}text"))
                self.assertEqual(text.text, label)
                self.assertEqual(text.get("font-weight"), "700")

    def test_spinner_arc_stays_visible_over_the_track(self):
        from balboa import branding
        result = subprocess.run([
            branding.image_tool(), "png:-", "-format",
            "%[fx:p{64,15}.a] %[fx:p{15,64}.a] %[fx:p{64,64}.a]", "info:"],
            input=branding.plymouth_assets()["spinner.png"], capture_output=True, check=True).stdout
        arc, track, center = map(float, result.split())
        self.assertEqual((arc, center), (1, 0))
        self.assertGreater(track, 0)
        self.assertLess(track, arc)

    def test_render_creates_three_pngs_with_manifest_and_embedded_bytes(self):
        import base64
        import contextlib
        import hashlib
        import struct
        from balboa import branding
        from balboa.cli import parser
        site = self.root / "site.json"
        site.write_text(json.dumps({**self.site, "branding_text": "Site label"}))
        output = self.root / "branded"
        args = parser().parse_args(["render", "--flavor", "laptop", "--site", str(site),
                                   "--disk", "vda", "--output", str(output), "--branding-text", "Test & Lab", "--no-boot-splash"])
        with contextlib.redirect_stdout(io.StringIO()):
            render(args)
        metadata = json.loads((output / "installation.json").read_text())
        self.assertFalse(metadata["boot_splash"])
        manifest = metadata["branding"]
        self.assertEqual(manifest["text"], "Test & Lab")
        self.assertTrue((output / "branding/inter.pf2").read_bytes().startswith(b"FILE"))
        self.assertEqual(manifest["sources"]["font"]["version"], "4.1")
        self.assertEqual({p.name for p in (output / "branding").glob("*.png")}, set(branding.SIZES))
        ks = (output / "installation.ks").read_text()
        for name, size in branding.SIZES.items():
            data = (output / "branding" / name).read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), size)
            self.assertEqual(manifest["images"][name]["sha256"], hashlib.sha256(data).hexdigest())
            self.assertIn(base64.b64encode(data).decode(), ks)
        alpha = subprocess.run([
            shutil.which("magick") or shutil.which("convert"), str(output / "branding/login.png"),
            "-format", "%[fx:minima.a] %[fx:maxima.a] %[fx:p{0,0}.a]", "info:"],
            capture_output=True, text=True, check=True).stdout
        self.assertEqual(alpha, "0 1 0")
        server, _ = render_text("server", self.site, "vda", "dvd")
        self.assertIn(branding.BOOT_DIR + "/boot.png", server)
        self.assertNotIn(" > " + branding.DESKTOP_DIR + "/wallpaper.png", server)
        self.assertNotIn(" > " + branding.DESKTOP_DIR + "/login.png", server)

    def test_render_reads_site_key_and_does_not_disclose_it_in_metadata(self):
        import contextlib
        from balboa.cli import parser
        secret = "a private integration test passphrase"
        site = self.root / "site.json"
        site.write_text(json.dumps({**self.site, "luks_passphrase": secret}))
        site.chmod(0o600)
        output = self.root / "rendered"
        args = parser().parse_args(["render", "--flavor", "laptop", "--site", str(site),
                                   "--disk", "nvme0n1", "--output", str(output)])
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            render(args)
        record = (output / "installation.json").read_text()
        self.assertEqual(json.loads(record)["luks_passphrase_source"], "site")
        self.assertTrue(json.loads(record)["luks_passphrase_embedded"])
        self.assertNotIn(secret, record)
        self.assertNotIn(secret, stdout.getvalue())

    def test_lab_requires_isolated_disk_and_generated_secret(self):
        for disk, secret in (("sda", "a" * 40), ("vda", None), ("vda", 'x"\n%post')):
            with self.subTest(disk=disk), self.assertRaises(ValueError):
                render_text("server", self.site, disk, "dvd", True, secret)
        text, _ = render_text("server", self.site, "vda", "dvd", True, "a" * 40)
        self.assertIn('--passphrase="' + "a" * 40 + '"', text)
        self.assertIn("cmdline\n", text)

    def test_flavors_select_correct_profile_and_source(self):
        for flavor in ("server", "workstation", "laptop"):
            for kind in ("dvd",):
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
                    self.assertEqual("\ndnf-automatic\n" in text, flavor != "server")
                    self.assertEqual(" > /etc/dnf/automatic.conf\n" in text, flavor != "server")
                    self.assertEqual(" > /etc/systemd/system/dnf-automatic.service.d/60-balboa-guard.conf\n" in text,
                                     flavor != "server")

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

    def test_tailoring_changes_only_the_declared_vendor_and_mail_rules(self):
        profile_id, text = tailoring("server", PROFILE)
        root = ET.fromstring(text)
        profile = root.find("x:Profile", NS)
        self.assertEqual(profile.get("extends"), PROFILE)
        self.assertEqual(profile.get("id"), profile_id)
        selections = profile.findall("x:select", NS)
        self.assertEqual({s.get("idref") for s in selections}, {"xccdf_org.ssgproject.content_rule_" + r for r in EXCLUSIONS})
        self.assertTrue(all(s.get("selected") == "false" for s in selections))

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

    def test_evidence_frame_ignores_firmware_console_output(self):
        data = self.archive("evidence/summary.json").read_bytes()
        stream = self.root / "evidence.stream"
        marker = b"\nBALBOA_EVIDENCE_V1\n"
        stream.write_bytes(b"\x1b[2JUEFI console output" + marker + data)
        decoded = self.root / "decoded.tar.gz"
        decode_evidence(stream, decoded)
        self.assertEqual(decoded.read_bytes(), data)
        for content in (data, marker + b"invalid", marker + data + marker):
            stream.write_bytes(content)
            with self.subTest(content=len(content)), self.assertRaises(ValueError):
                decode_evidence(stream, decoded)

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
        (self.root / "sshd.txt").write_text("active\n")
        (self.root / "native-final.json").write_text('{"passed": true}\n')
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
        config.write_text(f"PROFILE={PROFILE}\nBASE_PROFILE={PROFILE}\nLAB=no\nFLAVOR=workstation\nDESKTOP=no\n")
        replacements = {"/etc/balboa/image.conf": str(config), "/var/lib/balboa": str(state),
                        "/etc/dnf/dnf.conf": str(self.root / "dnf.conf"),
                        "/etc/balboa/initial-repos.d": str(self.root / "initial-repos.d"),
                        "/etc/aide.conf": str(self.root / "aide.conf"),
                        "/usr/local/libexec/balboa": str(guest), "/var/lib/aide": str(aide),
                        "/usr/share/xml/scap/ssg/content": str(content)}
        for name in ("harden.sh", "audit.sh", "failure.sh", "result_gate.py", "package_source.py"):
            text = (repository / "guest" / name).read_text()
            for old, new in replacements.items():
                text = text.replace(old, new)
            (guest / name).write_text(text)
        (self.root / "aide.conf").touch()
        (guest / "native_checks.py").write_text('print("{\\"passed\\": true}")\n')
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
