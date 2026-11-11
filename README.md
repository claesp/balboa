# Balboa

Balboa creates custom Rocky Linux 10 installation images for servers, workstations, and laptops.
A Kickstart file controls an installation.
An ISO is a file that contains installation media.

The project customizes official Rocky Linux media with Kickstart files.
Installation and initial hardening use only packages from the locked DVD.
Later updates use the configured Rocky repositories and the laptop EPEL repository.
The source lock fixes the media version, image identity, and signing key. [Source lock](sources.lock.json)
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
| Server | Boot essentials, the OpenSSH server, and common security tools |
| Workstation | The common minimum, a minimal GNOME desktop, automatic security updates, and Firefox |
| Laptop | The minimal GNOME desktop, automatic security updates, Firefox, wireless networking, Bluetooth, firmware, and power management |

The server excludes desktop, wireless, Bluetooth, and graphics firmware packages.
The workstation and laptop omit an SSH server by default.
See [Minimal flavors](docs/flavors.md) for package boundaries and hardware requirements.

## Storage and security

Production images use a fixed 128 GB disk budget by default.
GB means 1,000,000,000 bytes in this project.
Test images use 32 GB by default with the same partition scheme.

LVM divides storage into separate logical volumes.
All persistent filesystems except boot filesystems use encrypted LVM storage.
The layout uses separate filesystems for temporary files, system logs, and audit logs.
These filesystems use mount restrictions where applicable.
See [Fixed storage](docs/storage.md) for allocation sizes and configuration.

The images use security profiles based on CIS Level 2.
The profiles contain two declared policy differences.
OpenSCAP applies the selected profile and assesses the installed system after a restart.
The project does not claim CIS certification or conformance to an unmodified benchmark.

Production builds require a root console password.
SSH root login remains disabled.
The optional `luks_passphrase` site field supplies the disk encryption key during unattended installation.
Set the values for central logging at deployment.
See [Security policy](docs/security.md) and [Site configuration](docs/site.md) before production release.

## Documentation

Use the document that matches your task.

| Task | Document |
| --- | --- |
| Prepare the host and create installation ISOs | [Build and installation](docs/build.md) |
| Add files to the installed system | [Add custom files](docs/build.md#add-custom-files) |
| Configure the graphical boot and encrypted disk prompt | [Boot process](docs/boot.md) |
| Set the logo text and generate boot and desktop images | [Boot and desktop images](docs/branding.md) |
| Select packages and hardware support | [Minimal flavors](docs/flavors.md) |
| Examine X1 Carbon Gen 13 compatibility and hardware tests | [Lenovo X1 Carbon Gen 13](docs/lenovo-x1.md) |
| Examine DVD package restrictions and review missing packages | [Package sources](docs/package-sources.md) |
| Examine Firefox privacy policies and update behavior | [Firefox browser](docs/browser.md) |
| Manage desktop security updates and repositories | [Desktop package updates](docs/updates.md) |
| Set disk sizes and mount restrictions | [Fixed storage](docs/storage.md) |
| Supply credentials and central logging configuration | [Site configuration](docs/site.md) |
| Examine security controls and release conditions | [Security policy](docs/security.md) |
| Do Podman and QEMU tests | [Testing](docs/testing.md) |
| Start a laptop ISO in a QEMU window | [Interactive QEMU tests](docs/qemu.md) |
| Examine recorded results and remaining hardware tests | [Verification record](docs/verification.md) |
| Change sources, packages, and security content | [Maintenance](docs/maintenance.md) |
| Preview or remove obsolete build files | [Clean generated files](docs/clean.md) |

## Repository contents

The flavor definitions select packages for each system role. [Flavor definitions](flavors/)
The Kickstart template and storage policy define the common installation. [Kickstart template](kickstarts/base.ks.in) · [Storage policy](storage/layout.json)
The guest programs apply and assess the security policy. [Guest programs](guest/)

The build commands create media and operate test machines. [Build commands](balboa/)
The container definitions supply build tools and the local test log receiver. [Container definitions](containers/)
The tests assess input restrictions, image contents, and security results. [Tests](tests/)

Use lab media only in disposable virtual machines.
Lab media contains disposable passwords and disk encryption secrets.
Git excludes generated images, reports, and credentials under `build/` and `cache/`.
