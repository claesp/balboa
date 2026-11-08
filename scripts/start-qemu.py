#!/usr/bin/env python3
"""Start an installation ISO or boot an existing disposable QEMU disk."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("The value must be greater than zero.")
    return number


def firmware_pair(code=None, variables=None):
    if code or variables:
        if not code or not variables:
            raise ValueError("Set both --ovmf-code and --ovmf-vars.")
        candidates = [(code, variables)]
    else:
        candidates = [(Path(directory) / f"OVMF_CODE{suffix}.fd", Path(directory) / f"OVMF_VARS{suffix}.fd")
                      for directory in ("/usr/share/OVMF", "/usr/share/edk2/ovmf")
                      for suffix in ("_4M", "")]
    for code, variables in candidates:
        if code.is_file() and variables.is_file():
            return code.resolve(), variables.resolve()
    raise ValueError("Install OVMF, set its two paths, or select --firmware bios.")


def prepare(args):
    work = args.workdir.resolve()
    disk = work / "system.qcow2"
    state = work / "machine.json"
    if "," in str(work):
        raise ValueError("The VM directory path cannot contain commas.")
    if args.boot:
        if args.disk_size_gb or args.disk_device:
            raise ValueError("Disk size and device configuration apply only to a new installation.")
        if not state.is_file() or state.is_symlink() or not disk.is_file() or disk.is_symlink():
            raise ValueError("The VM requires its original machine.json and regular virtual disk file.")
        record = json.loads(state.read_text())
        if args.firmware and args.firmware != record["firmware"]:
            raise ValueError("Boot the disk with the firmware that created it.")
        info = json.loads(subprocess.check_output(["qemu-img", "info", "--output=json", str(disk)], text=True))
        if info["format"] != "qcow2" or info["virtual-size"] != record["disk_bytes"] or "backing-filename" in info:
            raise ValueError("The disk format or size differs from the recorded VM.")
    else:
        iso = args.iso.resolve()
        if not iso.is_file() or "," in str(iso):
            raise ValueError("Select a regular ISO file with no commas in its path.")
        if work.exists() and any(work.iterdir()):
            raise ValueError(f"The VM directory is not empty: {work}. Use --boot to reuse its disk, or select a new directory.")
        manifest_path = iso.with_suffix(".json")
        manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
        expected_bytes = manifest.get("storage", {}).get("disk_bytes", 128_000_000_000)
        if type(expected_bytes) is not int or expected_bytes <= 0:
            raise ValueError("The ISO manifest requires a positive disk size in bytes.")
        size = args.disk_size_gb * 1_000_000_000 if args.disk_size_gb else expected_bytes
        if type(size) is not int or size <= 0 or size < expected_bytes:
            raise ValueError("The virtual disk must contain the fixed image layout. Render a smaller layout for a smaller disk.")
        device = args.disk_device or manifest.get("disk", "vda")
        if manifest.get("disk", device) != device:
            raise ValueError("The virtual disk device must match the Kickstart disk in the ISO manifest.")
        record = {"disk_bytes": size, "disk_device": device, "firmware": args.firmware or "uefi"}
    if record["disk_device"] not in ("vda", "sda", "nvme0n1") or record["firmware"] not in ("bios", "uefi"):
        raise ValueError("Use BIOS or UEFI and a Kickstart disk named vda, sda, or nvme0n1.")
    if record["firmware"] == "uefi":
        if args.boot and not args.ovmf_code and not args.ovmf_vars:
            code = Path(record["ovmf_code"])
        else:
            code, variables = firmware_pair(args.ovmf_code, args.ovmf_vars)
        if not code.is_file() or "," in str(code):
            raise ValueError("The OVMF code file is absent or its path contains commas.")
        record["ovmf_code"] = str(code)
        nvram = work / "OVMF_VARS.fd"
        if args.boot and (not nvram.is_file() or nvram.is_symlink()):
            raise ValueError("The original writable OVMF variable file is absent.")
    if not args.boot:
        work.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Reserve the new filename without truncating an existing file.
        with disk.open("xb"):
            pass
        try:
            subprocess.run(["qemu-img", "create", "-f", "qcow2", str(disk), str(size)], check=True)
            if record["firmware"] == "uefi":
                shutil.copyfile(variables, nvram)
            with state.open("x") as output:
                json.dump(record, output, indent=2)
                output.write("\n")
        except BaseException:
            disk.unlink(missing_ok=True)
            raise
    return work, record


def command(args, work, record):
    accel = args.accel
    if accel == "auto":
        accel = "kvm" if os.access("/dev/kvm", os.R_OK | os.W_OK) else "tcg"
    disk = work / "system.qcow2"
    argv = ["qemu-system-x86_64", "-machine", f"q35,accel={accel}",
            "-cpu", "host" if accel == "kvm" else "max", "-smp", str(args.cpus),
            "-m", str(args.memory_mib), "-display", args.display, "-device", "virtio-vga",
            "-device", "qemu-xhci", "-device", "usb-tablet", "-nic", "user,model=virtio-net-pci",
            "-monitor", "none", "-serial", "stdio", "-serial", f"file:{work / ('evidence-' + str(time.time_ns()) + '.stream')}"]
    device = record["disk_device"]
    if device == "vda":
        argv += ["-drive", f"file={disk},format=qcow2,if=virtio"]
    else:
        argv += ["-drive", f"file={disk},format=qcow2,if=none,id=systemdisk"]
        if device == "nvme0n1":
            argv += ["-device", "nvme,drive=systemdisk,serial=balboa-test"]
        else:
            argv += ["-device", "virtio-scsi-pci,id=scsi0", "-device", "scsi-hd,drive=systemdisk,bus=scsi0.0"]
    if record["firmware"] == "uefi":
        argv += ["-drive", f'if=pflash,format=raw,unit=0,readonly=on,file={record["ovmf_code"]}',
                 "-drive", f"if=pflash,format=raw,unit=1,file={work / 'OVMF_VARS.fd'}"]
    if args.iso:
        argv += ["-drive", f"file={args.iso.resolve()},format=raw,media=cdrom,readonly=on", "-boot", "once=d"]
    return argv


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--iso", type=Path, help="Install an ISO on a new disposable disk.")
    mode.add_argument("--boot", action="store_true", help="Boot the existing disk without installation media.")
    result.add_argument("--workdir", type=Path, default=ROOT / "build/qemu-laptop",
                        help="VM directory. Default: %(default)s.")
    result.add_argument("--disk-size-gb", type=positive, help="Decimal GB. Default: ISO manifest size, or 128 GB.")
    result.add_argument("--disk-device", choices=("vda", "sda", "nvme0n1"), help="Default: ISO manifest disk, or vda.")
    result.add_argument("--firmware", choices=("bios", "uefi"), help="Default: UEFI for installation, recorded firmware for boot.")
    result.add_argument("--ovmf-code", type=Path)
    result.add_argument("--ovmf-vars", type=Path)
    result.add_argument("--accel", choices=("auto", "kvm", "tcg"), default="auto")
    result.add_argument("--display", choices=("gtk", "sdl", "none"), default="gtk")
    result.add_argument("--memory-mib", type=positive, default=4096)
    result.add_argument("--cpus", type=positive, default=4)
    return result


def main():
    args = parser().parse_args()
    os.umask(0o077)
    for tool in ("qemu-system-x86_64", "qemu-img"):
        if not shutil.which(tool):
            raise ValueError(f"Install {tool} on the build host.")
    work, record = prepare(args)
    print(f"The VM disk is {work / 'system.qcow2'}.", flush=True)
    print("Use the QEMU window and this terminal for installation and disk unlock.", flush=True)
    return subprocess.run(command(args, work, record)).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
