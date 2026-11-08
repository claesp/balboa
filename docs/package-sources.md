# Package sources

Installation and initial hardening use only the locked Rocky Linux DVD package versions.
Later approved updates use the official Rocky repositories.
This policy applies to packages installed in the target system.
The build tools use the separate pinned Rocky container.

## Build requirements

The render and ISO commands use DVD media by default.
They reject the network boot ISO as an installation source.
The Kickstart selects `cdrom` and defines no additional repositories.

The package preflight operates in a Podman container with network access disabled.
It reads BaseOS and AppStream metadata from the authenticated DVD.
It resolves the mandatory core group, explicit packages, kernel, dependencies, and exclusions against those repositories only.

Every ISO build requires this package preflight.
The test also requires the current initial hardening guard in the Kickstart.
Old Kickstart files require a new render before an ISO build.

Operate these commands from the repository root on the build host:

```sh
python3 -m balboa fetch --kind dvd
python3 -m balboa render --flavor laptop --lab --output build/laptop-dvd-lab
python3 -m balboa validate build/laptop-dvd-lab/installation.ks --packages
python3 -m balboa iso build/laptop-dvd-lab/installation.ks --output build/laptop-dvd-lab.iso
```

The preflight writes `installation.dvd-packages.json` beside the Kickstart.
The ISO command copies this report beside its output with the `.dvd-packages.json` suffix.
The ISO manifest records the report digest, DVD identity, and source policy.

## Initial hardening

The installed DNF configuration selects an empty repository directory before first boot.
This prevents repository package downloads during initial hardening.
The hardening service also denies IP traffic from its own processes.

The native assessment compares every installed package version and architecture with the DVD inventory before and after remediation.
The pinned key assessment covers imported signing keys separately.
Any package outside that inventory stops initial hardening and requires review.

Desktop hardening temporarily masks PackageKit so that background updates cannot change packages during AIDE initialization.
The service restores the normal repository configuration before it creates the AIDE database.
It assesses the package inventory again before it marks initial hardening complete.
It then removes the temporary PackageKit mask and restarts the system.

If initial hardening fails, the failure handler restores the repository restriction.
Examine the retained evidence before corrections.
Do not create the `remediated` marker to bypass this restriction.

## Later updates

Successful initial hardening restores the normal official Rocky repositories.
GNOME Software and DNF can then apply approved updates.
These updates can contain versions that did not exist on the installation DVD.

Later assessments retain the package exclusions and signing-key tests.
They do not require updated packages to match the original DVD versions.
Retain the initial DVD assessment with later update and assessment records.

The locked DVD contains a known security content defect described in [Build and installation](build.md#dvd-media).
Complete initial hardening before the documented security content update.
Retain the original results and repeat the assessment after the approved update.

## Packages outside the DVD

The builder does not download a missing package from another repository.
It reports that the package requires review and stops.
No off-DVD exception is currently approved for installation or initial hardening.

For a package review, record these facts in `docs/`:

- Package name, version, architecture, and required hardware feature
- Reason that the DVD package selection cannot supply the feature
- Official source, signing identity, and package digest
- Dependency versions and their sources
- Security effects, maintenance owner, and update procedure
- Installation and hardware test evidence
- Reviewer decision and the resulting source policy change

A review record alone does not bypass the build restriction.
An approved exception requires an explicit reviewed implementation change or a newly reviewed DVD source.
Do not add a network repository to the Kickstart as a workaround.

## DVD inventory changes

Epoch is the RPM version ordering number.
The file `data/dvd-packages.json` records the exact DVD package identities.
Each identity contains the name, epoch, version, release, and architecture.

After a reviewed DVD source change, fetch its authenticated media on the build host.
Regenerate the inventory with `xorriso` available on that host:

```sh
python3 scripts/catalog-dvd.py cache/Rocky-10.2-x86_64-dvd1.iso
```

Replace the filename with the reviewed filename in `sources.lock.json`.
The script requires a matching DVD digest before it writes the inventory.
Review the inventory diff and repeat all flavor preflights and installation tests before release.
