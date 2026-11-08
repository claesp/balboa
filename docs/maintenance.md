# Maintenance

The repository separates source selection, flavor data, and common controls.
The renderer combines these inputs into one Kickstart file.
The ISO builder retains the official boot structure.

## Repository files

Use these locations for changes:

- `sources.lock.json` contains official media identities and the container digest.
- `flavors/` contains package selections and security profile identifiers.
- `kickstarts/` contains the common installation template.
- `storage/` contains fixed disk sizes and the LVM allocation policy.
- `data/keyboards.json` contains supported XKB layout names and their source package identity.
- `guest/` contains the installed hardening and assessment programs.
- `balboa/` contains the commands for builds and tests.
- `tests/` contains tests for security boundaries and image contents.
- `docs/` contains the operating procedures and security decisions.

The renderer accepts restricted site fields.
It does not interpret site values as shell commands.
The generated files use access permissions for the build account only.

Use [Clean generated files](clean.md) to preview and remove obsolete local outputs.
The clean command retains generated images and virtual disks unless you select them explicitly.

## Change a flavor

Edit the relevant file in `flavors/` on the build host.
Keep the Level 2 profile identifier unless the security owner approves a separate policy.
Record package and policy decisions in `docs/`.

Package names belong in the `packages` array.
Environment groups use the Kickstart `@^` prefix.
The default flavors deliberately avoid full desktop environment groups.
Common packages belong in `kickstarts/base.ks.in`.

After a change, use a new output directory.
The renderer does not update an existing artifact.
Previously generated media still contains the previous programs and policy.

Before a release commit, do these tasks:

1. Do the local tests with `make test`.
2. Render each affected flavor into a new directory.
3. Do the Podman tests for each generated Kickstart.
4. Build each affected ISO from authenticated media.
5. Do the QEMU installation and assessment for each affected flavor.
6. Examine the manual controls and physical hardware requirements.
7. Record the results and limitations in `docs/`.
8. Commit the source changes without generated credentials or images.

## Update official sources

Rocky supports the current minor release of each major version.
The lock deliberately prevents an automatic media version change.
The installed package repositories still receive updates.

Before a source change, examine the official Rocky release notes.
Obtain the new digest file and detached signature from the official ISO directory.
Make sure that GnuPG accepts the signature against the approved Rocky key.

Compare the signing key fingerprint with the approved Rocky release key.
Do not replace the trusted fingerprint because a download presents a different key.
An unreviewed key change removes the authentication boundary.

Record the new ISO filename and digest in `sources.lock.json`.
Record the official container digest in the same file.
Rebuild the tools and do all flavor tests after the source change.
For a DVD change, regenerate and review `data/dvd-packages.json` through [Package sources](package-sources.md).

For keyboard catalog updates, use `rules/base.xml` from the official Rocky `xkeyboard-config` package.
Retain layout identifiers only when the package supplies their files under `/usr/share/X11/xkb/symbols/`.
Record the package identity in `data/keyboards.json` after the update.

## Update installed systems

Apply package updates through the approved site maintenance process.
Do not rely on the installer ISO for later security updates.
The default image does not define a site update schedule.

After an update, retain the previous assessment evidence.
Do another assessment through the procedure in [Security policy](security.md).
Record changes to the kernel and security content with the results.

The default image creates the initial AIDE database.
The site must define later AIDE assessments and alert handling.
The site must also define central log retention and capacity alerts.

## Evidence handling

Keep ISO manifests with the corresponding image.
Keep installed package records with the corresponding assessment report.
Restrict access to lab secrets and account password digests.

The project does not upload generated images or reports.
The Git ignore file excludes `build/`, `cache/`, and `site.json`.
Use a controlled artifact store for release media and retained evidence.
