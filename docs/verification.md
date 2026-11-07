# Verification record

The test session covers November 7 and November 8, 2026.
The build host uses x86_64 Linux with QEMU, Podman, and KVM.
The source media is the authenticated Rocky Linux 10.2 boot ISO.

## Completed tests

The local suite contains 22 passing tests.
It includes site input restrictions, report assessment, guest archive restrictions, and expected OpenSCAP exit handling.
The suite also tests the serial unlock procedure and installer error detection.

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
The installer tests do not prove that the CIS assessment passes.

## Content identity

The tool image contains `scap-security-guide-0.1.82-2.el10_2.rocky.1.1`.
The tool image contains OpenSCAP version 1.4.4.
The datastream contains both selected CIS Level 2 profile titles.

The repository records the official media identities in `sources.lock.json`.
Each built ISO has a separate manifest and package record.
Each installed assessment records its own content digest and package list.

## Remaining release evidence

Full CIS conformance requires the release procedure in [Security policy](security.md).
Parser tests and completed installations do not prove conformance.
The current test record does not claim a passing CIS assessment.

DVD installation, UEFI USB boot, and Secure Boot require separate tests.
Laptop wireless operation, suspend, resume, and docking require physical hardware tests.
Site controls require an approved benchmark review and retained evidence.
