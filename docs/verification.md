# Verification record

The test session covers November 7 and November 8, 2026.
The build host uses x86_64 Linux with QEMU, Podman, and KVM.
The source media is the authenticated Rocky Linux 10.2 boot ISO.

## Completed tests

The local suite contains 31 passing tests.
It includes site input restrictions, report assessment, guest archive restrictions, and expected OpenSCAP exit handling.
The suite also tests the serial unlock procedure and installer error detection.
The local suite accepts matching root console and administrator password digests for all three flavors.
Six launcher tests cover disk preservation, manifest constraints, boot reuse, and private UEFI variable files.

All three flavors pass the RHEL10 Kickstart parser.
All guest shell programs pass Bash syntax tests.
The systemd service definitions pass inspection with their executable paths present.
The minimal post-installation script passes the disposable container test for all three flavors.

All three flavors pass the package availability test against official BaseOS and AppStream repositories.
The ISO tests accept the embedded Kickstart contents for all three flavors.
The tests also accept the BIOS and UEFI optical boot structures.

All three current minimal flavors complete installation on fixed 32 GB encrypted LVM disks.
The server and laptop complete BIOS installation.
The workstation completes UEFI installation.

Each installer reports the completion marker after its post-installation scripts.
The scripts use a separate administrator identity and explicit audit and SELinux dependencies.

## Automatic assessment results

Each final image completes remediation, AIDE initialization, and an automatic restart.
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

## Content identity

The tool image contains `scap-security-guide-0.1.82-2.el10_2.rocky.1.1`.
The tool image contains OpenSCAP version 1.4.4.
The datastream contains both selected CIS Level 2 profile titles.

The repository records the official media identities in `sources.lock.json`.
Each built ISO has a separate manifest and package record.
Each installed assessment records its own content digest and package list.

The implementation revision is `f9bc899`.
The current renderer exactly reproduces all three tested Kickstart files.
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

The final ISO files use `build/balboa-FLAVOR-acceptance-lab.iso`.
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
The full installation tests use 32 GB disks.
The local suite tests the 128 GB allocation calculation and fixed sizes.
Production media still requires interactive installation tests with site credentials and deployed logging configuration.

DVD installation, UEFI USB boot, and Secure Boot require separate tests.
The other BIOS and UEFI flavor combinations require separate tests.
Laptop wireless operation, suspend, resume, and docking require physical hardware tests.
Site controls require an approved benchmark review and retained evidence.
