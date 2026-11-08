# CP69net X1 Carbon Gen 13 test image

The build date is November 8, 2026.
The image uses the private `cp69net.json` file without changes to its contents.
The latest laptop flavor includes the DVD package restriction, audio additions, Firefox policies, and GNOME Software.

## Artifacts

The ISO is `build/balboa-cp69net-laptop-x1-carbon-gen13-20261108.iso`.
Its size is 10235871232 bytes, or approximately 9.53 GiB.
Use a USB device with at least 16 GB of capacity.
The SHA-256 digest is:

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

## Installation behavior

The Kickstart targets `nvme0n1` and uses the fixed 128 GB production layout.
The installer erases the entire selected disk, including existing partitions outside that layout.
Before starting installation, make sure that `nvme0n1` identifies the intended disk on the X1.
Do not boot this unattended installation media on another machine without a disk selection review.

The image enables the configured graphical boot splash.
The installed system requires the LUKS passphrase at each boot.
The installation ends with a poweroff.
Remove the installation USB device before starting the installed system.

The site file does not configure central log upload.
Supply the deployment logging configuration before the production security assessment.
The initial DVD security content retains its documented account-shell assessment defect.
Use [Updated security content](security.md#updated-security-content) after successful initial hardening.

## Build procedure

Operate these commands from the repository root on the build host:

```sh
python3 -m balboa render --flavor laptop --site cp69net.json --disk nvme0n1 --disk-size-gb 128 --output build/cp69net-x1-carbon-gen13-20261108
python3 -m balboa iso build/cp69net-x1-carbon-gen13-20261108/installation.ks --usb-uefi --output build/balboa-cp69net-laptop-x1-carbon-gen13-20261108.iso
```

These output paths already exist after this build.
For another build, select new output paths.

The build uses the authenticated Rocky Linux 10.2 DVD.
The offline dependency test resolves 624 packages with the production splash enabled.
The tool container adds `mtools-4.0.43-7.el10` and its matching `glibc-gconv-extra-2.39-121.el10_2` dependency from that DVD.
These additions affect the build tools, not the target package selection.

## Results and limits

All 59 local tests pass.
Kickstart syntax, guest shell syntax, and security profile tests pass.
The embedded Kickstart matches the rendered file byte for byte.
Both BIOS and UEFI optical boot entries select that Kickstart.
The appended UEFI partition contains the matching customized GRUB configuration and unchanged signed boot programs.
The embedded media checksum assessment reports `PASS`.

QEMU boots this ISO as a read-only USB device and shows the Rocky UEFI installation menu.
The disposable test VM contains no installation disk and no network interface.
A second USB boot starts Anaconda and reads the embedded Kickstart.
Anaconda reports `Disk 'nvme0n1' given in ignoredisk command does not exist.` because the test contains no target disk.
These tests establish USB boot and installer behavior without an installation on a target disk.
The earlier [DVD policy test](verification.md#dvd-package-policy-and-x1-review) supplies the full laptop installation and hardening results.
Physical installation, Secure Boot, and device acceptance on the X1 remain pending.
Use [Lenovo X1 Carbon Gen 13](lenovo-x1.md) for those acceptance requirements.

The build logs reside in the render directory.
The USB boot screenshots and QEMU record reside in `build/x1-usb-boot-20261108/`.
