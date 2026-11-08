import configparser
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from balboa.cli import iso, parser
from balboa.dvd import catalog
from balboa.vm import inspect_dvd_evidence
from guest import package_source


class DVDTests(unittest.TestCase):
    def test_host_requires_all_initial_dvd_attestations(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            manifest = {"package_source_policy": {"installation": "locked-dvd-only"}}
            with self.assertRaisesRegex(ValueError, "lacks initial DVD"):
                inspect_dvd_evidence(manifest, evidence)
            for name in ("native-before.json", "native-after.json", "native-initial-complete.json"):
                (evidence / name).write_text(json.dumps({"passed": True, "dvd_package_versions": "passed"}))
            inspect_dvd_evidence(manifest, evidence)
            (evidence / "native-after.json").write_text(json.dumps({"passed": True, "dvd_package_versions": "failed"}))
            with self.assertRaisesRegex(ValueError, "did not pass"):
                inspect_dvd_evidence(manifest, evidence)

    def test_every_installation_command_defaults_to_dvd(self):
        commands = (["fetch"], ["render", "--flavor", "server", "--lab", "--output", "build/example"],
                    ["iso", "build/example/installation.ks", "--output", "build/example.iso"])
        for command in commands:
            self.assertEqual(parser().parse_args(command).kind, "dvd")
        with self.assertRaisesRegex(ValueError, "locked DVD"):
            iso(SimpleNamespace(kind="boot"))

    def test_dvd_inventory_matches_locked_media(self):
        record = catalog()
        self.assertEqual(record["packages"], sorted(set(record["packages"])))
        self.assertGreater(len(record["packages"]), 5000)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "catalog.json"
            path.write_text(json.dumps({**record, "dvd_sha256": "0" * 64}))
            with patch("balboa.dvd.CATALOG", path), self.assertRaisesRegex(ValueError, "source lock"):
                catalog()

    def test_initial_package_versions_reject_non_dvd_updates(self):
        identity = "example|0|1.0|1.el10|x86_64"
        record = {"packages": [identity]}
        package_source.validate_installed([identity, "gpg-pubkey|0|key|date|(none)"], record)
        for packages in ([], [identity.replace("1.0", "2.0")], [identity.replace("|0|", "|1|")],
                         [identity.replace("x86_64", "aarch64")], ["unreviewed|0|1|1|noarch"]):
            with self.subTest(packages=packages), self.assertRaises(ValueError):
                package_source.validate_installed(packages, record)

    def test_repository_guard_preserves_hardening_and_restores_vendor_paths(self):
        for original in (None, "/etc/yum.repos.d,/etc/vendor.repos.d"):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                configuration = root / "dnf.conf"
                state = root / "state.json"
                guard = root / "guard"
                configuration.write_text("[main]\ngpgcheck=False\n" +
                                         (f"reposdir={original}\n" if original else ""))
                with patch.multiple(package_source, CONFIGURATION=configuration, STATE=state, GUARD=str(guard)):
                    package_source.guard(True)
                    package_source.guard(True)
                    data = configparser.ConfigParser()
                    data.read(configuration)
                    self.assertEqual(data["main"]["reposdir"], str(guard))
                    data["main"]["gpgcheck"] = "True"
                    with configuration.open("w") as output:
                        data.write(output)
                    package_source.guard(False)
                    released = configparser.ConfigParser()
                    released.read(configuration)
                    self.assertEqual(released["main"].get("reposdir"), original)
                    self.assertTrue(released["main"].getboolean("gpgcheck"))
                    self.assertFalse(state.exists())

    def test_guard_rejects_added_repositories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "guard"
            directory.mkdir()
            (directory / "unreviewed.repo").touch()
            configuration = root / "dnf.conf"
            configuration.write_text("[main]\ngpgcheck=True\n")
            with patch.multiple(package_source, CONFIGURATION=configuration, STATE=root / "state", GUARD=str(directory)):
                with self.assertRaisesRegex(ValueError, "remain empty"):
                    package_source.guard(True)


if __name__ == "__main__":
    unittest.main()
