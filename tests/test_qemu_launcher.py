import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("qemu_launcher", Path(__file__).resolve().parents[1] / "scripts/start-qemu.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.iso = self.root / "laptop.iso"
        self.iso.write_bytes(b"test ISO")
        self.iso.with_suffix(".json").write_text(json.dumps({"disk": "nvme0n1", "storage": {"disk_bytes": 32_000_000_000}}))
        self.work = self.root / "machine"

    def tearDown(self):
        self.temp.cleanup()

    def arguments(self, *extra):
        return launcher.parser().parse_args(["--workdir", str(self.work), *extra])

    def install(self):
        args = self.arguments("--iso", str(self.iso), "--firmware", "bios")
        with patch.object(launcher.subprocess, "run"):
            return args, *launcher.prepare(args)

    def test_manifest_selects_disk_size_and_nvme_device(self):
        args, work, record = self.install()
        self.assertEqual(record["disk_bytes"], 32_000_000_000)
        self.assertEqual(record["disk_device"], "nvme0n1")
        command = launcher.command(args, work, record)
        self.assertIn("nvme,drive=systemdisk,serial=balboa-test", command)
        self.assertIn("once=d", command)
        self.assertNotIn("-no-reboot", command)

    def test_installation_never_truncates_an_existing_disk(self):
        self.work.mkdir()
        disk = self.work / "system.qcow2"
        disk.write_bytes(b"keep the existing disk")
        args = self.arguments("--iso", str(self.iso))
        with patch.object(launcher.subprocess, "run") as run, self.assertRaises(ValueError):
            launcher.prepare(args)
        self.assertEqual(disk.read_bytes(), b"keep the existing disk")
        run.assert_not_called()

    def test_disk_budget_and_device_must_match_the_image(self):
        for extra in (("--disk-size-gb", "24"), ("--disk-device", "vda")):
            args = self.arguments("--iso", str(self.iso), *extra)
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                launcher.prepare(args)
            self.assertFalse(self.work.exists())

    def test_boot_rejects_a_disk_symlink_or_backing_file(self):
        _, work, _ = self.install()
        disk = work / "system.qcow2"
        disk.unlink()
        disk.symlink_to(self.iso)
        args = self.arguments("--boot")
        with self.assertRaises(ValueError):
            launcher.prepare(args)
        disk.unlink()
        disk.touch()
        info = {"format": "qcow2", "virtual-size": 32_000_000_000, "backing-filename": "/dev/example"}
        with patch.object(launcher.subprocess, "check_output", return_value=json.dumps(info)), self.assertRaises(ValueError):
            launcher.prepare(args)

    def test_boot_preserves_recorded_device_and_omits_the_installer(self):
        _, work, expected = self.install()
        args = self.arguments("--boot")
        info = {"format": "qcow2", "virtual-size": 32_000_000_000}
        with patch.object(launcher.subprocess, "check_output", return_value=json.dumps(info)):
            _, record = launcher.prepare(args)
        self.assertEqual(record, expected)
        command = launcher.command(args, work, record)
        self.assertNotIn("-boot", command)
        self.assertFalse(any("media=cdrom" in item for item in command))
        self.assertIn("user,model=virtio-net-pci", command)

    def test_uefi_keeps_a_private_copy_of_the_variable_template(self):
        code, variables = self.root / "code.fd", self.root / "vars.fd"
        code.write_bytes(b"code")
        variables.write_bytes(b"original firmware variables")
        args = self.arguments("--iso", str(self.iso), "--ovmf-code", str(code), "--ovmf-vars", str(variables))
        with patch.object(launcher.subprocess, "run"):
            work, record = launcher.prepare(args)
        (work / "OVMF_VARS.fd").write_bytes(b"changed VM variables")
        self.assertEqual(variables.read_bytes(), b"original firmware variables")
        command = launcher.command(args, work, record)
        self.assertIn(f"if=pflash,format=raw,unit=0,readonly=on,file={code}", command)
