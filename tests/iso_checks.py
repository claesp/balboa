"""Inspect customized ISO boot entries and embedded Kickstart contents."""

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso")
    parser.add_argument("kickstart")
    parser.add_argument("--files-sha256", required=True)
    parser.add_argument("--usb-uefi", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from guest.install_files import payload_digest

    iso, ks = args.iso, args.kickstart
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in ("installation.ks", "install_files.py", "balboa-files", "EFI/BOOT/grub.cfg", "boot/grub2/grub.cfg"):
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["xorriso", "-osirrox", "on", "-indev", iso, "-extract", "/" + name, str(destination)],
                           check=True, capture_output=True)
        if (root / "installation.ks").read_bytes() != Path(ks).read_bytes():
            raise ValueError("The embedded Kickstart differs from the reviewed file.")
        if (root / "install_files.py").read_bytes() != (Path("/workspace/guest") / "install_files.py").read_bytes():
            raise ValueError("The ISO contains a different file installer.")
        if payload_digest(root / "balboa-files") != args.files_sha256:
            raise ValueError("The ISO files differ from the selected files or permissions.")
        print("The ISO files and permissions match the selected files.")
        for config in (root / "EFI/BOOT/grub.cfg", root / "boot/grub2/grub.cfg"):
            lines = [line for line in config.read_text().splitlines() if line.strip().startswith(("linux ", "linuxefi "))]
            if not lines or any("inst.ks=" not in line or "installation.ks" not in line for line in lines):
                raise ValueError("A boot entry does not select the embedded Kickstart.")
        result = subprocess.run(["xorriso", "-indev", iso, "-report_el_torito", "plain"],
                                check=True, capture_output=True, text=True)
        report = result.stdout + result.stderr
        if "BIOS" not in report or "UEFI" not in report:
            raise ValueError("The ISO does not contain both BIOS and UEFI boot entries.")
        if args.usb_uefi:
            system = subprocess.run(["xorriso", "-indev", iso, "-report_system_area", "plain"],
                                    check=True, capture_output=True, text=True)
            match = re.search(r"GPT start and size\s*:\s*2\s+(\d+)\s+(\d+)", system.stdout + system.stderr)
            if not match:
                raise ValueError("The ISO lacks the expected UEFI USB partition.")
            image = str(Path(iso).resolve()) + "@@" + str(int(match[1]) * 512)
            for name in ("grub.cfg", "BOOTX64.EFI", "grubx64.efi", "mmx64.efi"):
                original = root / "EFI/BOOT" / name
                if not original.exists():
                    subprocess.run(["xorriso", "-osirrox", "on", "-indev", iso, "-extract",
                                    "/EFI/BOOT/" + name, str(original)], check=True, capture_output=True)
                actual = root / ("usb-" + name)
                subprocess.run(["mcopy", "-i", image, "::/EFI/BOOT/" + name, str(actual)], check=True)
                if actual.read_bytes() != original.read_bytes():
                    raise ValueError("The UEFI USB partition differs from the reviewed EFI file: " + name)
            print("UEFI USB configuration and signed boot programs match the ISO files.")
        print("Embedded Kickstart and BIOS/UEFI optical boot entries passed inspection.")


if __name__ == "__main__":
    main()
