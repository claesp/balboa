# Verification record

The test session covers November 7 and November 8, 2026.
The build host uses x86_64 Linux with QEMU, Podman, and KVM.
The tests use authenticated Rocky Linux 10.2 boot and DVD media.

## Completed tests

The local suite contains 41 passing tests.
It includes site input restrictions, report assessment, guest archive restrictions, and expected OpenSCAP exit handling.
The suite also tests the serial unlock procedure and installer error detection.
The local suite accepts matching root console and administrator password digests for all three flavors.
Six launcher tests cover disk preservation, manifest constraints, boot reuse, and private UEFI variable files.
Keyboard tests reject `sv` and `se-latin1` where XKB layout identifiers are required.
The Swedish layout `se` renders correctly for all three flavors.
The Rocky container preflight accepts `se` and rejects `sv` before ISO creation.
Encryption tests cover site JSON passphrases, quoted characters, file permissions, and rejected control characters.
The tests require the passphrase to remain absent from manifests and console output.
The LUKS boundary tests accept five characters and reject four characters.
The image tests assess literal text, generated PNG dimensions, manifest digests, and embedded bytes.

All three flavors pass the RHEL10 Kickstart parser.
All guest shell programs pass Bash syntax tests.
The systemd service definitions pass inspection with their executable paths present.
The minimal post-installation script passes the disposable container test for all three flavors.

All three flavors pass the package availability test against official BaseOS and AppStream repositories.
The ISO tests accept the embedded Kickstart contents for all three flavors.
The tests also accept the BIOS and UEFI optical boot structures.

The earlier acceptance images complete installation on fixed 32 GB encrypted LVM disks.
The server and laptop complete BIOS installation.
The workstation completes UEFI installation.

Each installer reports the completion marker after its post-installation scripts.
The scripts use a separate administrator identity and explicit audit and SELinux dependencies.

## Automatic assessment results

The following results describe the earlier acceptance images under `build/acceptance/`.
Each image completes remediation, AIDE initialization, and an automatic restart.
The next boot does an assessment without remediation.
The final results contain no failed, erroneous, unknown, or untested selected rules.

| Flavor | Firmware | Passing rules | Not applicable | Findings |
| --- | --- | --- | --- | --- |
| Server | BIOS | 420 | 17 | 0 |
| Workstation | UEFI | 429 | 3 | 0 |
| Laptop | BIOS | 429 | 3 | 0 |

These results apply to the tailored profiles in [Security policy](security.md).
The profiles contain two declared differences from the packaged base profiles.
The results do not claim certification or conformance to an unmodified benchmark.

All three final native assessments accept the pinned Rocky signing keys and package exclusions.
The native assessments also accept the private journal key ownership and mode.
All three host assessments accept the fixed disk size, encrypted LVM sources, and required mount restrictions.

The server reports an active SSH service after remediation.
Its final package list excludes the unwanted graphics and Intel wireless firmware.
All three systems report enforcing SELinux and zero failed systemd units.

All three journal upload services report an active state and a successful result.
The retained upload logs contain no upload errors.
The local TLS receiver retains events from all three hostnames.
It rejects connections that omit a client certificate.

The receiver offers HTTP/1.1 to avoid the observed systemd 257 HTTP/2 buffer error.
Private key access uses a restricted group because Rocky SELinux policy blocks the default systemd credential label.
The tests retain SELinux enforcement throughout both corrections.

The production policy requires a root console password.
Production log receiver values remain deployment-time configuration.
The lab images use disposable root passwords and a local authenticated receiver.

## Interactive launcher results

The interactive script passes QEMU device initialization for BIOS and UEFI.
Each firmware mode accepts the `vda`, `sda`, and `nvme0n1` disk devices.
The startup tests use the laptop DVD ISO, temporary disks, a headless display, and paused guest CPUs.

These startup tests do not replace the full installation and security assessments recorded in this document.
The GTK window requires examination in a graphical host session.
See [Interactive QEMU tests](qemu.md) for the installation and later boot commands.

## Unattended 128 GB installation

The laptop DVD completes installation on a 128 GB NVMe disk with UEFI.
The recorded test uses revision `51f764f` with disposable credentials and its former passphrase-file input.
The `luks_passphrase` site field reproduces the tested storage commands.
The keyboard layout is Swedish `se`.

The guest disk is `nvme0n1` and contains exactly 128000000000 bytes.
Anaconda marks Installation Destination as completed before partition creation.
The installer creates EFI and boot partitions, an encrypted physical volume, and all eight specified logical volumes.

The installer requests no LUKS setup passphrase.
Its post-installation programs report `BALBOA_INSTALL_COMPLETE`, and the machine powers off.
The fixed 128 GB allocation requires no size correction.

This test uses the official DVD kernel and initrd with serial console arguments.
It covers installation and storage preparation.
The completed CIS assessment results remain those from the 32 GB tests.

The private test artifacts remain under `build/luks-storage-check/`.
The serial log is `vm-nvme-uefi/install.log` under that directory.
The file `installation-summary.json` records the result without the passphrase.

The disposable DVD ISO has this SHA256 digest:

```text
76a95dc318565c1a8be67419b02e4949802ee513384c8a5aab3ce05444af5d04
```

## Content identity

The tool image contains `scap-security-guide-0.1.82-2.el10_2.rocky.1.1`.
The tool image contains OpenSCAP version 1.4.4.
The datastream contains both selected CIS Level 2 profile titles.

The repository records the official media identities in `sources.lock.json`.
Each built ISO has a separate manifest and package record.
Each installed assessment records its own content digest and package list.

The implementation revision is `f9bc899`.
These earlier images precede the generated branding assets.
All three assessments use this datastream SHA256 digest:

```text
4985708fcfe92ff3a4ddb88ac1d6a9a3ec887c545032d7a7d592669670917213
```

These SHA256 digests identify the exact disposable ISO files from this session:

| Flavor | ISO digest |
| --- | --- |
| Server | `94e87b0dca74b73e7eef866766664320d69fa25317076eb82ff5dadb81d41486` |
| Workstation | `9d54f817020df5980b7d4d77296b3cf9eacc33e7f59ec907378b7f424e85a184` |
| Laptop | `189ce0fbe0ecc00e08f89f450a46d6f0f3c0104112cbfe4a8aaf6af3e118d075` |

## Local artifacts

The earlier acceptance ISO files use `build/balboa-FLAVOR-acceptance-lab.iso`.
Replace `FLAVOR` with `server`, `workstation`, or `laptop`.
Each ISO has a matching JSON manifest and tool package list.

The generated Kickstart files and disposable secrets remain under `build/acceptance/FLAVOR/`.
The collected results use these directories:

- `build/acceptance/vm-server-bios/collected/evidence/`
- `build/acceptance/vm-workstation-uefi/collected/evidence/`
- `build/acceptance/vm-laptop-bios/collected/evidence/`

Each directory contains the HTML report, XML results, native assessments, and system records.
The collector journals remain under `build/lab-logging/logs/`.
The test session stops the collector after all final assessments pass.

Git excludes generated images, reports, and disposable credentials.
Retain release evidence in the approved artifact store.
Lab certificates expire after two days.
Create a new collector directory and new lab media for later test sessions.

## Remaining release evidence

Full CIS conformance requires the release procedure in [Security policy](security.md).
Passing automatic assessments do not cover every manual or organizational control.
The full CIS assessment tests use 32 GB disks.
The local suite tests the 128 GB allocation calculation and fixed sizes.
Production media still requires tests with actual site credentials and deployed logging configuration.

The remaining DVD flavor and firmware combinations require separate installation tests.
UEFI USB boot and Secure Boot require separate tests.
The other BIOS and UEFI flavor combinations require separate tests.
Laptop wireless operation, suspend, resume, and docking require physical hardware tests.
Site controls require an approved benchmark review and retained evidence.

## Generated boot and desktop images

The November 8 image tests cover all three minimal flavors.
The renderer creates three PNG files with the selected text.
The manifest digests match the generated files and the embedded Kickstart bytes.

All three baseline container tests pass with the generated assets.
The workstation and laptop tests read the wallpaper and login values through GNOME.
The tests also require GDM to read the login image.

The branded laptop completes a DVD installation on a fixed 32 GB UEFI virtual disk.
A QEMU screenshot shows the generated boot image behind the installed GRUB menu.
Another screenshot shows the custom login banner and `Powered by Rocky Linux`.

A separate server test uses a five-character LUKS passphrase from site JSON.
The official Rocky DVD installer creates the encrypted LVM layout without an encryption setup prompt.
The installer completes its installation scripts and powers off.

The local evidence resides under `build/branding-test/`.
The test directories contain disposable credentials and remain outside version control.
The five-character test uses a separate small ISO for the rendered Kickstart and the official DVD for packages.

The initial DVD assessment records 425 passing controls and one account-shell finding.
The finding includes a trailing line break in the final administrator shell path.
It matches the [known security content defect](https://github.com/ComplianceAsCode/content/pull/14751).
The original report remains in `collected-dvd-original/evidence/` under the laptop VM directory.

The test VM receives security content updates through the official Rocky repositories.
The updated packages are `scap-security-guide-0.1.82-2.el10_2.rocky.1.1` and `openscap-scanner-1.4.4-1.el10_2`.
The GNOME session shows the generated default wallpaper after login.
The installed image digests match the render manifest after hardening.

After the content update, the branded laptop completes remediation and a fresh assessment after restart.
The assessment records 429 passing controls, three not applicable controls, and no findings.
The native Rocky tests, encrypted LVM tests, and package boundary tests pass.

The final system reports enforcing SELinux and zero failed systemd units.
The authenticated journal upload service reports an active state and a successful result.
The test session stops its temporary receiver after assessment.

The updated results reside in `build/branding-test/vm-laptop-uefi/collected/evidence/`.
The boot, login, and desktop screenshots remain in that VM directory.
The branding implementation revision is `6368828`.

The branded laptop DVD ISO has this SHA256 digest:

```text
8241deb0ca20d5cc6c09084ef9223b188f518cec116c1fbcf38397f4771c4d3e
```
