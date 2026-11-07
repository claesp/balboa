"""Inspect customized ISO boot entries and embedded Kickstart contents."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    iso, ks = sys.argv[1:]
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in ("installation.ks", "EFI/BOOT/grub.cfg", "boot/grub2/grub.cfg"):
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["xorriso", "-osirrox", "on", "-indev", iso, "-extract", "/" + name, str(destination)],
                           check=True, capture_output=True)
        if (root / "installation.ks").read_bytes() != Path(ks).read_bytes():
            raise ValueError("The embedded Kickstart differs from the reviewed file.")
        for config in (root / "EFI/BOOT/grub.cfg", root / "boot/grub2/grub.cfg"):
            lines = [line for line in config.read_text().splitlines() if line.strip().startswith(("linux ", "linuxefi "))]
            if not lines or any("inst.ks=" not in line or "installation.ks" not in line for line in lines):
                raise ValueError("A boot entry does not select the embedded Kickstart.")
        result = subprocess.run(["xorriso", "-indev", iso, "-report_el_torito", "plain"],
                                check=True, capture_output=True, text=True)
        report = result.stdout + result.stderr
        if "BIOS" not in report or "UEFI" not in report:
            raise ValueError("The ISO does not contain both BIOS and UEFI boot entries.")
        print("Embedded Kickstart and BIOS/UEFI optical boot entries passed inspection.")


if __name__ == "__main__":
    main()
