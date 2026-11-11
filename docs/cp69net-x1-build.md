# CP69net X1 Carbon Gen 13 test images

## November 9 UEFI USB build

This build uses revision `4d5e8e5`, the private `cp69net.json` file, and `--usb-uefi`.
The ISO is `build/balboa-cp69net-laptop-x1-carbon-gen13-20261109-usb.iso`.
Its size is 10234363904 bytes, or approximately 9.53 GiB.

The build includes English and Swedish locales, the GNOME defaults, and hostnames from firmware serial numbers.
The offline package test resolves 633 packages from the locked Rocky Linux 10.2 DVD.
See [Desktop Settings](desktop-settings.md) and [Hostname](site.md#hostname) for the installed behavior.

Use a USB device with at least 16 GB of capacity.
The installer erases the entire `nvme0n1` disk and creates the fixed 128 GB layout.
Keep the ISO private because it contains the configured LUKS passphrase.

The embedded media checksum reports `PASS`.
The SHA-256 digest is the value that follows.

```text
8247a505cc62acda9b31f29b0c45d87622af46b618c1f87d6d646a4cfa615a7f
```

QEMU started Anaconda from a read-only UEFI USB device.
Anaconda read the embedded Kickstart.
The test stopped at disk selection because the VM had no NVMe installation disk.
The build host kept this ISO as the only ISO in `build/`.
Cleanup discarded the temporary files from the build and boot test.

## November 9 Abisko build

This build uses revision `dde9e90` and the private `cp69net.json` site file.
The wallpaper and boot image use the Abisko photo.
Both images show its credit in the lower left corner.
Plymouth puts the rotating ring at the center of the screen.
The transparent login image is identical to the image in the previous build.
See [Boot and desktop images](branding.md) for the photo source and image files.

DNF Automatic installs security updates after initial hardening and the first assessment.
Use DNF to install packages and manage repositories.
See [Desktop package updates](updates.md) for the commands and schedule.

The build wrote the ISO to `build/balboa-cp69net-laptop-x1-carbon-gen13-20261109-abisko.iso`.
Its size is 10234363904 bytes, or approximately 9.53 GiB.
Use a USB device with at least 16 GB of capacity.
The installer erases the entire `nvme0n1` disk and creates the fixed 128 GB layout.
Keep the ISO private because it contains the configured LUKS passphrase.

The render and build log reside in `build/cp69net-x1-20261109-abisko/`.
The offline package test resolves 611 packages from the locked Rocky Linux 10.2 DVD.
The build wrote the manifest and the `.iso.sha256` checksum file beside the ISO.

```text
934adc3838a8cdd1d2e1d110bfdc65dd9819782b004ca9d3bd94327c5a5ec8fa
```

The embedded media checksum reports `PASS`.
QEMU started Anaconda from a read-only UEFI USB device.
Anaconda read the embedded Kickstart.
The test stopped at disk selection because the VM had no NVMe installation disk.
The USB boot test records reside in `build/x1-usb-boot-20261109-abisko/`.

A separate QEMU test on an installed lab system shows the centered ring and the disk prompt.
The photo credit stays visible on the 1280 × 800 screen.
The visual test records reside in `build/abisko-review-final/`.

## November 9 build

This build uses revision `feabd13` and the private `cp69net.json` site file.
The boot image, wallpaper, and login banner show the configured name in Inter Bold.
Plymouth uses the rotating ring and the revised disk prompt.
The image configures the approved Rocky and EPEL sources and the stable LVFS firmware remote after initial hardening.
The laptop uses RPM sources for desktop applications.

The build wrote the ISO to `build/balboa-cp69net-laptop-x1-carbon-gen13-20261109.iso`.
Its size is 10235871232 bytes, or approximately 9.53 GiB.
Use a USB device with at least 16 GB of capacity.
The installer erases the entire `nvme0n1` disk and creates the fixed 128 GB layout.
Keep the ISO private because it contains the configured LUKS passphrase.

The render and build log reside in `build/wordmark-x1/`.
The offline preflight resolves 624 packages from the locked Rocky Linux 10.2 DVD.
The build wrote the manifest and the `.iso.sha256` checksum file beside the ISO.

```text
7d1e6df22031673bcf33cf947a0028bf025f9f69e5ab71c37dae006831359cac
```

The embedded media checksum reports `PASS`.
The UEFI USB partition contains the updated Kickstart reference and the signed Rocky boot programs.
QEMU started Anaconda from the read-only USB device.
Anaconda read the embedded Kickstart.
The test stopped at the expected disk selection step because the VM had no NVMe installation disk.
The boot test records reside in `build/x1-usb-boot-20261109/`.

## November 8 build

The image uses the private `cp69net.json` file without changes to its contents.
This build includes the DVD package restriction, audio additions, Firefox policies, and GNOME Software.

### Artifacts

The build wrote the ISO to `build/balboa-cp69net-laptop-x1-carbon-gen13-20261108.iso`.
Its size is 10235871232 bytes, or approximately 9.53 GiB.
Use a USB device with at least 16 GB of capacity.
The SHA-256 digest is the following value.

```text
5b29cc874eb1c5a081769064319b51e280216731dd4420afa8c4655061cea863
```

The checksum file uses the `.iso.sha256` suffix.
The ISO manifest uses `.json`, and the offline package report uses `.dvd-packages.json`.
The build tool package record uses `.packages.txt`.
The render directory is `build/cp69net-x1-carbon-gen13-20261108/`.
The three generated images reside in its `branding/` directory.

The ISO and Kickstart contain the configured plaintext LUKS passphrase and account password digests.
Keep these artifacts private.
Their file permissions permit access only by the build account.
The repository does not contain the private site file or these generated artifacts.

### Installation behavior

The Kickstart targets `nvme0n1` and uses the fixed 128 GB production layout.
The installer erases the entire selected disk, including existing partitions outside that layout.
Before starting installation, make sure that `nvme0n1` identifies the intended disk on the X1.
Do not boot this unattended installation media on another machine without a disk selection review.

The image enables the configured graphical boot splash.
The installed system requires the LUKS passphrase at each boot.
The installer powers off the system at the end of installation.
Before you start the installed system, disconnect the installation USB device.

The site file does not configure central log upload.
Supply the deployment logging configuration before the production security assessment.
The initial DVD security content retains its documented account-shell assessment defect.
Use [Updated security content](security.md#updated-security-content) after successful initial hardening.

### Build procedure

Operate the following commands from the repository root on the build host.

```sh
python3 -m balboa render --flavor laptop --site cp69net.json --disk nvme0n1 --disk-size-gb 128 --output build/cp69net-x1-carbon-gen13-20261108
python3 -m balboa iso build/cp69net-x1-carbon-gen13-20261108/installation.ks --usb-uefi --output build/balboa-cp69net-laptop-x1-carbon-gen13-20261108.iso
```

This build used the output paths in the example.
If a path already exists, select a new path for the next build.

The build uses the authenticated Rocky Linux 10.2 DVD.
The offline dependency test resolves 624 packages with the production splash enabled.
The tool container adds `mtools-4.0.43-7.el10` and its matching `glibc-gconv-extra-2.39-121.el10_2` dependency from that DVD.
These packages apply only to the build tools.

### Results and limits

All 59 local tests pass.
Kickstart syntax, guest shell syntax, and security profile tests pass.
The embedded Kickstart matches the rendered file byte for byte.
Both BIOS and UEFI optical boot entries select that Kickstart.
The appended UEFI partition contains the matching customized GRUB configuration and unchanged signed boot programs.
The embedded media checksum assessment reports `PASS`.

QEMU booted this ISO as a read-only USB device.
QEMU showed the Rocky UEFI installation menu.
The disposable test VM had no installation disk and no network interface.

The second USB boot started Anaconda.
Anaconda read the embedded Kickstart.
Anaconda reports `Disk 'nvme0n1' given in ignoredisk command does not exist.` because the test contains no target disk.
These tests establish USB boot and installer behavior without an installation on a target disk.

The earlier [DVD policy test](verification.md#dvd-package-policy-and-x1-review) supplies the full laptop installation and hardening results.
Physical installation, Secure Boot, and device acceptance on the X1 remain pending.
Use [Lenovo X1 Carbon Gen 13](lenovo-x1.md) for those acceptance requirements.

The build logs reside in the render directory.
The USB boot screenshots and QEMU record reside in `build/x1-usb-boot-20261108/`.
