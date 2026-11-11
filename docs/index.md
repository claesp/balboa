# Balboa

Start at the [project overview](../README.md) for the main documentation links.

Balboa creates custom Rocky Linux 10 installation images.
A Kickstart file controls an installation.
An ISO is a file that contains installation media.

Balboa uses official Rocky Linux media and packages.
The source lock records the image digest and signing key.
A digest is a value that identifies file contents.

## Source acquisition

Operate this command on the Linux build host.
The host requires Python 3.11 or later, curl, and GnuPG.
The command authenticates the signed digest before it accepts the ISO.

```sh
python3 -m balboa fetch --kind dvd
```

The source lock selects Rocky Linux 10.2 for x86_64.
Rocky Linux requires an x86-64-v3 processor for this architecture.
The builder requires DVD packages for installation and initial hardening.
Package updates still require network access.
Balboa retains signature files in `cache/`.

## Project procedures

- Build production media from the selected sources. [Build and installation](build.md)
- Review the controls and release conditions. [Security policy](security.md)
- Do Podman and QEMU tests. [Testing](testing.md)
- Install an ISO in QEMU and access the desktop. [Interactive QEMU tests](qemu.md)
- Change sources and policies. [Maintenance](maintenance.md)
- Remove obsolete output and recover disk space. [Clean generated files](clean.md)
- Review completed tests and release evidence. [Verification record](verification.md)
- Review the spinner, graphical disk prompt, and startup behavior. [Boot process](boot.md)
- Generate images with the configured name. [Boot and desktop images](branding.md)
- Select packages and hardware services. [Minimal flavors](flavors.md)
- Review GNOME defaults and file selection. [Desktop Settings](desktop-settings.md)
- Review Firefox privacy policies and package updates. [Firefox browser](browser.md)
- Manage automatic security updates and repositories. [Desktop package updates](updates.md)
- Review DVD restrictions and missing packages. [Package sources](package-sources.md)
- Review hardware compatibility and physical acceptance requirements. [Lenovo X1 Carbon Gen 13](lenovo-x1.md)
- Configure disk sizes, LVM, and mount restrictions. [Fixed storage](storage.md)
- Configure hostnames, locales, recovery credentials, and central logging. [Site configuration](site.md)

## Source references

These references identify upstream behavior.
The source review date is November 7, 2026.
The source lock requires a separate review after each release change.

- [Rocky Linux releases](https://docs.rockylinux.org/latest/releases/)
- [Official Rocky Linux installation media](https://dl.rockylinux.org/pub/rocky/10/isos/x86_64/)
- [Rocky Linux 10 signing key](https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-10)
