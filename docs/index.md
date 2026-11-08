# Balboa

Start at the [project overview](../README.md) for the main documentation links.

Balboa creates custom Rocky Linux 10 installation images.
Kickstart is a file that controls an installation.
An ISO is a file that contains installation media.

Balboa uses official Rocky Linux media and packages.
The source lock records the image digest and signing key.
A digest is a value that identifies file contents.

The documentation uses Simplified Technical English.
No tool guarantees ASD-STE100 compliance.
The official dictionary is free at [asd-ste100.org](https://asd-ste100.org/).

## Source acquisition

Operate these commands on the Linux build host.
The host requires Python 3.11 or later, curl, and GnuPG.
The command authenticates the signed digest before it accepts the ISO.

```sh
python3 -m balboa fetch --kind boot
python3 -m balboa fetch --kind dvd
```

The source lock selects Rocky Linux 10.2 for x86_64.
Rocky Linux requires an x86-64-v3 processor for this architecture.
The boot ISO requires network access during installation.

The DVD contains packages for installation without network access.
Package updates still require network access.
Balboa retains signature files in `cache/`.

## Project procedures

[Build and installation](build.md) describes production media and source selection.
[Security policy](security.md) describes the controls and release conditions.
[Testing](testing.md) describes Podman and QEMU tests.
[Interactive QEMU tests](qemu.md) describes the script for ISO installation and desktop access.
[Maintenance](maintenance.md) describes source and policy changes.
[Clean generated files](clean.md) describes output removal and disk space recovery.
[Verification record](verification.md) records completed tests and release evidence.
[Boot process](boot.md) describes the spinner, graphical disk prompt, and startup choices.
[Boot and desktop images](branding.md) describes the generated logo, text, and images.
[Minimal flavors](flavors.md) describes package selection and hardware services.
[Fixed storage](storage.md) describes disk sizes, LVM, and mount restrictions.
[Site configuration](site.md) describes recovery credentials and central logging.

## Source references

These references identify upstream behavior.
The source review date is November 7, 2026.
The source lock requires a separate review after each release change.

- [Rocky Linux releases](https://docs.rockylinux.org/latest/releases/)
- [Official Rocky Linux installation media](https://dl.rockylinux.org/pub/rocky/10/isos/x86_64/)
- [Rocky Linux 10 signing key](https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-10)
