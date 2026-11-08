# Interactive QEMU tests

To remove an obsolete VM directory, use the selected-path procedure in [Clean generated files](clean.md).
The clean command shows its paths before removal and requires `--apply` to erase them.

The script `scripts/start-qemu.py` starts an ISO in a QEMU window.
An ISO is a file that contains installation media.
The script creates a disposable virtual disk and retains it for later boots.

The Linux host requires Python 3.11 or later, `qemu-system-x86_64`, and `qemu-img`.
The default window requires the QEMU GTK backend and a graphical session on the host.
UEFI requires OVMF firmware on the host.
See [Build and installation](build.md) for the image build procedure.

## Start the laptop ISO

Operate this command from the repository root after the laptop ISO build.
Replace the example ISO path with the image that you want to install.
Use a new VM directory for each installation.
The `--workdir` parameter selects the directory for the virtual disk and saved VM state.
Its default is `build/qemu-laptop` under the repository root, regardless of the current working directory.

```sh
./scripts/start-qemu.py --iso build/balboa-laptop-dvd.iso --workdir build/qemu-laptop
```

The default configuration uses UEFI, four virtual CPUs, and 4096 MiB of memory.
KVM uses host hardware to accelerate the virtual machine.
If the host account can access `/dev/kvm`, the script selects KVM.
Otherwise, it selects CPU emulation with the QEMU `max` model.

The script reads the JSON manifest beside a Balboa ISO.
If you copy an ISO, copy its matching JSON manifest beside it.
It uses the manifest disk size and device name.
The script supports `vda`, `sda`, and `nvme0n1` as installation disk names.
The startup summary shows the guest disk name, capacity, and firmware.

Without a manifest, the script creates a 128 GB disk named `vda`.
GB means 1,000,000,000 bytes.
The virtual disk file consumes host storage as the guest writes data.

The script refuses installation into a directory that contains files.
The error shows the full path of that directory.
Use `--boot` to reuse its virtual disk, or select a new directory for another installation.
Remove the old directory only if you no longer require its virtual disk and saved state.
Removal erases the VM data in that directory.
It attaches a virtual disk and the selected ISO.
It exposes no inbound host port or shared host directory.

Use the QEMU window for the installer and GNOME desktop.
Use the terminal for serial prompts from lab media.
For production media, enter the disk encryption passphrase when the guest prompts.
For unattended installation, set `luks_passphrase` in the site JSON before the [image build](build.md#unattended-disk-encryption).
This supplies the installation key and still requires disk unlock at boot.

## Boot the installed disk

After the installer stops, operate this command from the repository root:

```sh
./scripts/start-qemu.py --boot --workdir build/qemu-laptop
```

The script reuses the recorded firmware, disk device, and virtual disk.
It boots without installation media.
UEFI retains a private variable file in the VM directory.

The first installed boot applies the security policy and requests a restart.
QEMU continues through that restart.
Enter the encryption passphrase again when the guest prompts.

Production logging values require the procedure in [Site configuration](site.md).
For a lab ISO with local logging credentials, start its matching receiver before the installed boot:

```sh
python3 -m balboa lab-logger --directory build/lab-logging
```

Use the collector directory that supplied the certificates for that lab ISO.
Lab certificates expire after two days.
Create new lab media and certificates after expiry.

Lab media stops the guest after its automatic assessment.
To examine the GNOME desktop afterward, do the `--boot` command again.
Each start retains a separate `evidence-*.stream` file for the second serial channel.

For automatic report collection and release conditions, use [Testing](testing.md) and [Security policy](security.md).
Virtual machines do not test physical wireless, Bluetooth, suspend, or docking behavior.

## Change the VM configuration

Use BIOS if OVMF is unavailable on the host.
Select the firmware when you create the VM:

```sh
./scripts/start-qemu.py --iso build/balboa-laptop-dvd.iso --workdir build/qemu-laptop-bios --firmware bios
```

For a smaller disk, first render and build an image with the smaller fixed layout.
The script refuses a disk smaller than the image manifest requires.
The following example requires a laptop lab ISO with a 32 GB layout:

```sh
./scripts/start-qemu.py --iso build/balboa-laptop-lab.iso --workdir build/qemu-laptop-lab --disk-size-gb 32
```

Use `--memory-mib` and `--cpus` to change memory and CPU allocation.
Use `--accel tcg` to select CPU emulation explicitly.
Use `--display sdl` for an SDL window or `--display none` for terminal access only.

If automatic firmware discovery fails, supply both host firmware paths:

```sh
./scripts/start-qemu.py --iso build/balboa-laptop-dvd.iso --workdir build/qemu-laptop-custom --ovmf-code /path/to/OVMF_CODE.fd --ovmf-vars /path/to/OVMF_VARS.fd
```

Operate `./scripts/start-qemu.py --help` for all script parameters.
The default UEFI procedure does not enable Secure Boot.
The [QEMU command reference](https://www.qemu.org/docs/master/system/invocation.html) describes the underlying device and display parameters.
