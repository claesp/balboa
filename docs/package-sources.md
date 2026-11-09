# Package sources

Installation and initial hardening use only the locked Rocky Linux DVD package versions.
Later approved updates use the configured Rocky repositories and the laptop EPEL repository.
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

The desktop update service waits for initial hardening and the first assessment to finish.
The hardening service restores the normal repository configuration before it creates the AIDE database.
It assesses the package inventory again before it marks initial hardening complete.
It then restarts the system for the assessment.

If initial hardening fails, the failure handler restores the repository restriction.
Examine the retained evidence before corrections.
Do not create the `remediated` marker to bypass this restriction.

## Later updates

Successful initial hardening restores the normal official Rocky repositories.
DNF and DNF Automatic can then apply updates under the [desktop update policy](updates.md).
These updates can contain versions that did not exist on the installation DVD.

## Laptop package and firmware sources

The laptop prepares CRB, Realtime, Extras, Plus, Security, and EPEL before it releases the DVD restriction.
BaseOS and AppStream supply the standard packages and updates.
EPEL means Extra Packages for Enterprise Linux.
The laptop uses the stable Fedora EPEL 10 repository with RPM signature checks.
The signing-key assessment permits the approved EPEL key only in the later package policy.

The approved EPEL certificate has fingerprint `7D8D15CBFC4E62688591FB2633D98517E37ED158`.
The certificate and stable repository configuration come from `epel-release-10-7.el10_1.noarch` in Rocky Extras.
The project prepares those files directly and keeps the package installation on the DVD.
The [Fedora signing-key list](https://fedoraproject.org/security/#current-openpgp-certificates) identifies the EPEL 10 key.
The [Rocky repository guide](https://docs.rockylinux.org/teams/rel_eng/repo/) describes the additional Rocky sources.

The stable Linux Vendor Firmware Service (LVFS) remote supplies firmware metadata through `fwupd`.
The image enables that remote for the laptop.
Firmware updates require a separate operator action and the site firmware review.
See the [fwupd command guide](https://github.com/fwupd/fwupd/blob/main/src/fwupdmgr.md) for remote status and metadata refresh.

The laptop uses RPM sources for desktop applications.
The package selection excludes GNOME Software, PackageKit, and Flatpak.

To update an existing Balboa laptop, open a terminal in a copy of this repository on that laptop.
After initial hardening completes, operate the command with administrator privileges.

```sh
sudo python3 guest/laptop_repos.py
```

The command updates the local repository configuration and approved signing-key list.
It accepts the policy file format from earlier Balboa laptop images.
It installs the EPEL public key file for DNF to use when it verifies EPEL packages.
Use the following commands on the laptop to see the sources.

```sh
dnf repolist --enabled
fwupdmgr get-remotes
```

## Assessment after updates

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
