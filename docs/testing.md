# Tests

Podman tests the installation syntax and packaged security content.
QEMU tests the installer, kernel, storage, and installed services.
A container does not supply evidence of full system conformance.
For an ISO installation in a QEMU window, use [Interactive QEMU tests](qemu.md).

## Local tests

Operate this command on the Linux build host.
The tests require Python 3.11 or later, ImageMagick with SVG support, Fontconfig, and a GRUB font converter.
The tests do not require network access or administrator privileges.

```sh
make test
```

The tests reject unsafe site values and disk selections.
They reject empty, ambiguous, and unresolved security reports.
They also reject unsafe files in guest evidence archives.
Image tests assess text restrictions, PNG dimensions, embedded bytes, and manifest digests.
The LUKS tests accept five characters and reject four characters.

## Podman tests

Prepare the tool container with the procedure in [Build and installation](build.md).
The lab command creates disposable credentials for all three flavors.
The command requires empty flavor directories under `build/`.

```sh
make lab
make validate
```

The tests use `ksvalidator -v RHEL10`.
They require the Rocky datastream and both CIS Level 2 profile titles.
They also do syntax tests of the guest shell scripts.

For package availability, add `--packages` on the build host.
This test requires network access to the official Rocky repositories.
It examines package names and installation environments before ISO creation.

```sh
python3 -m balboa validate build/laptop/installation.ks --packages
```

The parser does not assess package availability or installation behavior.
A successful parser result does not prove a successful installation.
Use QEMU for those tests.

## Post-installation test

The baseline test does the post-installation script in a disposable container.
It installs the explicit packages with weak dependencies disabled.
The container does not assess kernel or storage controls.
For desktop flavors, the test reads wallpaper and login image values through GNOME.
The test also requires the login image to remain readable by GDM.

Operate this example on the build host after the lab renderer.
Replace both flavor references to examine another flavor.
The container removes its filesystem after the test.

```sh
podman run --rm -v "$PWD:/workspace:ro" localhost/balboa-tools:10 bash /workspace/tests/smoke_baseline.sh /workspace/build/server/installation.ks server
```

## QEMU installation

For a complete logging assessment, start the local TLS collector first.
The collector uses Podman and requires OpenSSL on the build host.
The command publishes its port on host loopback only.

```sh
python3 -m balboa lab-logger --directory build/lab-logging
python3 -m balboa render --flavor server --lab --lab-logging-dir build/lab-logging/client --output build/server-logging
```

The certificate authority signs both disposable server and client certificates.
The certificates expire after two days.
HAProxy requires a trusted client certificate before it forwards an upload to the receiver.
The receiver accepts plain HTTP only through container loopback.
The TLS listener offers HTTP/1.1 to avoid a systemd 257 upload buffer error with HTTP/2.

QEMU reaches host loopback through its isolated network address `10.0.2.2`.
The lab renderer uses `https://10.0.2.2:19532` by default.
For another port, set `--port` on the collector and `--lab-logging-url` on the renderer.

Use separate output directories for workstation and laptop renders.
Each lab render creates a random root console password in its restricted secrets file.
Without the collector configuration, the final assessment reports the missing central logging control.

Use disposable lab images only for this automated procedure.
Lab media contains disk passphrases and disposable account credentials.
Do not install lab media on production hardware.

The example uses the server flavor and BIOS firmware.
The ISO command inspects the embedded Kickstart and both optical boot entries.
The QEMU command creates a new fixed-size virtual disk from the manifest.
The default lab disk contains 32 GB.

```sh
python3 -m balboa iso build/server-logging/installation.ks --output build/balboa-server-lab.iso
python3 -m balboa vm --iso build/balboa-server-lab.iso --workdir build/vm-server-bios --phase install
```

The virtual machine has no host disk or shared host directory.
The network uses QEMU address translation and exposes no inbound host port.
The serial log remains in the VM directory.

The installer stops through the Kickstart `poweroff` command.
QEMU exit alone does not prove installation success.
Examine the serial log before the first system boot.

## QEMU assessment

The first system boot applies the security profile.
The second system boot assesses the installed system.
The example unlocks the encrypted virtual disk through the serial console.

```sh
python3 -m balboa vm --iso build/balboa-server-lab.iso --workdir build/vm-server-bios --phase boot --lab-secrets build/server-logging/lab-secrets.json
python3 -m balboa vm --iso build/balboa-server-lab.iso --workdir build/vm-server-bios --phase boot --lab-secrets build/server-logging/lab-secrets.json
```

QEMU stops at each requested restart because the command uses `-no-reboot`.
An intermediate stop without evidence is not a passing assessment.
The final boot exports the evidence through a dedicated serial channel.

The host places the reports under `collected/evidence/` in the VM directory.
The host does another report assessment and requires encrypted storage and enforcing SELinux.
It also requires the fixed disk size, LVM mount sources, mount restrictions, and flavor package exclusions.
A failed rule causes the final command to return a nonzero status.

The collector retains journals under `build/lab-logging/logs/` on the host.
After the VM tests, stop the owned collector with this command:

```sh
python3 -m balboa lab-logger --directory build/lab-logging --stop
```

The command retains the journal files and disposable keys for examination.
Before a later test session, use a new directory for fresh certificates.

Before release, examine the HTML report and each manual control.
Do not release an image because the remediation service completed.
Use [Security policy](security.md) for release conditions.

## Firmware and flavor coverage

For UEFI, add `--firmware uefi` to all three VM commands.
Use a new VM directory for each firmware and flavor combination.
The default OVMF paths match common Debian installation paths.

If the host uses different paths, set `--ovmf-code` and `--ovmf-vars`.
For CPU emulation without KVM, add `--accel tcg`.
The emulated CPU uses the QEMU `max` model for x86-64-v3 instructions.

Do the installation and assessment for these combinations:

- Server with BIOS and UEFI
- Workstation with BIOS and UEFI
- Laptop with BIOS and UEFI

The default VM firmware does not enable Secure Boot.
Do separate Secure Boot tests with approved OVMF keys or physical firmware.
Do physical laptop tests before release.

## Production media tests

Default production media requests the encryption passphrase during installation.
Media built with a `luks_passphrase` site value supplies that installation key automatically.
Use an isolated virtual machine with a disposable disk for this test.
Select the same disk name in Kickstart as the virtual machine exposes.

Attach the production ISO through virt-manager or an equivalent QEMU interface.
Do not attach host block devices or shared host directories.
Use the graphical console to enter the passphrase and examine installer errors.
The status `Kickstart insufficient` means that storage configuration is incomplete.
It does not specifically report insufficient disk capacity.
See [Storage problems](storage.md#storage-problems) for the installation diagnostics.

After installation, do the two system boots with manual disk unlock.
Examine the reports through the installed system console.
Production media does not automatically export reports or stop after assessment.
