#!/usr/bin/env python3
"""Use the official Lorax ISO builder with an unmounted FAT image update."""

import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def rebuild_efi(input_iso, directory):
    image = tempfile.NamedTemporaryFile(prefix="balboa-efi-", suffix=".img")
    try:
        subprocess.run(["xorriso", "-osirrox", "on", "-overwrite", "on", "-indev", input_iso,
                        "-extract", "/images/efiboot.img", image.name], check=True, capture_output=True)
        Path(image.name).chmod(0o600)
        for name in ("grub.cfg", "BOOT.conf"):
            source = Path(directory) / "EFI/BOOT" / name
            if source.is_file():
                subprocess.run(["mcopy", "-o", "-i", image.name, str(source), "::/EFI/BOOT/" + name],
                               check=True)
        return image
    except BaseException:
        image.close()
        raise


def main():
    os.umask(0o077)
    if not shutil.which("mcopy"):
        raise RuntimeError("The tool container requires mtools. Rebuild it with python3 -m balboa tools.")
    loader = importlib.machinery.SourceFileLoader("lorax_mkksiso", "/usr/bin/mkksiso")
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    module.RebuildEFIBoot = rebuild_efi
    module.main()


if __name__ == "__main__":
    main()
