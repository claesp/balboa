import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import xml.etree.ElementTree as ET

from balboa.cli import checksum_entry
from balboa.render import render_text, valid_site
from balboa.vm import extract_evidence
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
                    self.assertEqual("NetworkManager-wifi" in text, flavor == "laptop")

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


if __name__ == "__main__":
    unittest.main()
