# Balboa

Balboa creates custom Rocky Linux 10 installation images for servers, workstations, and laptops.
Kickstart is a file that controls an installation.
An ISO is a file that contains installation media.

The project customizes official Rocky Linux media with Kickstart files.
The [source lock](sources.lock.json) fixes the media version, image identity, and signing key.
Podman supplies build tools and installation syntax tests.
QEMU supplies disposable virtual machines for installation and security tests.

Start with [Build and installation](docs/build.md) for host requirements and the image build procedure.
The detailed procedures and security decisions are in [docs/](docs/index.md).

## Minimal flavors

A flavor is a package selection for one system role.
All flavors start with mandatory core packages and the required security tools.
The installer excludes weak dependencies and default group additions.

| Flavor | Contents |
| --- | --- |
| Server | Boot essentials, OpenSSHD, and common security tools |
| Workstation | The common minimum and a minimal GNOME desktop |
| Laptop | The minimal GNOME desktop, wireless networking, Bluetooth, firmware, and power management |

The server excludes desktop, wireless, Bluetooth, and graphics firmware packages.
The workstation and laptop omit an SSH server by default.
See [Minimal flavors](docs/flavors.md) for package boundaries and hardware requirements.

## Storage and security

Production images use a fixed 128 GB disk budget by default.
GB means 1,000,000,000 bytes in this project.
Test images use 32 GB by default with the same partition scheme.

LVM divides storage into separate logical volumes.
All persistent filesystems except boot filesystems use encrypted LVM storage.
Separate temporary, log, and audit filesystems use mount restrictions where applicable.
See [Fixed storage](docs/storage.md) for allocation sizes and configuration.

The images use CIS Level 2 based security profiles with two declared policy differences.
OpenSCAP applies the selected profile and assesses the installed system after a restart.
The project does not claim CIS certification or conformance to an unmodified benchmark.

Production builds require a root console password.
SSH root login remains disabled.
Central logging values remain deployment-time configuration.
See [Security policy](docs/security.md) and [Site configuration](docs/site.md) before production release.

## Documentation

Use these documents for each project task:

| Task | Document |
| --- | --- |
| Prepare the host and create installation ISOs | [Build and installation](docs/build.md) |
| Select packages and hardware support | [Minimal flavors](docs/flavors.md) |
| Set disk sizes and mount restrictions | [Fixed storage](docs/storage.md) |
| Supply credentials and central logging configuration | [Site configuration](docs/site.md) |
| Examine security controls and release conditions | [Security policy](docs/security.md) |
| Do Podman and QEMU tests | [Testing](docs/testing.md) |
| Start a laptop ISO in a QEMU window | [Interactive QEMU tests](docs/qemu.md) |
| Examine recorded results and remaining hardware tests | [Verification record](docs/verification.md) |
| Change sources, packages, and security content | [Maintenance](docs/maintenance.md) |

## Repository contents

The [flavor definitions](flavors/) select packages for each system role.
The [Kickstart template](kickstarts/base.ks.in) and [storage policy](storage/layout.json) define the common installation.
The [guest programs](guest/) apply and assess the security policy.

The [build commands](balboa/) create media and operate test machines.
The [container definitions](containers/) supply build tools and the local test log receiver.
The [tests](tests/) assess input restrictions, image contents, and security results.

Use lab media only in disposable virtual machines.
Lab media contains disposable passwords and disk encryption secrets.
Git excludes generated images, reports, and credentials under `build/` and `cache/`.
