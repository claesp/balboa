# Build and installation

The build host requires an x86_64 Linux system.
Podman supplies Rocky Linux tools in a separate environment.
QEMU supplies a virtual machine for installation tests.

The host requires the following tools.

- Python 3.11 or later
- ImageMagick with SVG support and Fontconfig
- `grub2-mkfont` or `grub-mkfont` for the Inter boot font
- Curl and GnuPG
- Podman
- OpenSSL and OpenSSH tools
- QEMU system tools and `qemu-img`
- OVMF firmware for UEFI tests

Operate all repository commands from the repository root.
Reserve at least 30 GiB for the source DVD, one custom ISO, and a server test.
Reserve more space for desktop tests and retained evidence.

## Prepare the tools

The container base digest appears in `sources.lock.json`.
The container build installs its tools from the official Rocky repositories.
The container build requires network access.

```sh
python3 -m balboa tools
python3 -m balboa fetch --kind dvd
```

The source command requires a matching signature, signing key, and ISO digest.
The lock file fixes the media version.
The command retains the downloaded ISO for later builds.
Target installation and initial hardening use only the locked DVD package versions.
See [Package sources](package-sources.md) for enforcement and the review procedure for missing packages.

## Create production media

Copy the site example on the build host.
The example contains placeholders that the renderer rejects.
The site file contains the administrator account information.

```sh
cp examples/site.json site.json
chmod 600 site.json
```

Create the password digest on the build host. The first command prompts for the account password.
Create the SSH key on the same host. The second command prompts for the private key passphrase.

```sh
openssl passwd -6
ssh-keygen -t ed25519 -f ~/.ssh/balboa_operator
```

Put the password digest in `password_hash` in `site.json`.
Put the root console password digest in `root_password_hash` in `site.json`.
Both password fields can contain the same digest.
Retain the root password in the approved recovery vault.

Put the public key contents in `ssh_public_key` in `site.json`.
Set the installation hostname and locale fields in `site.json`.
See [Hostname](site.md#hostname) for the name that the installed system uses.
Use an XKB layout identifier for `keyboard`, such as `se` for Swedish or `us` for US English.
See [Keyboard and language](site.md#keyboard-and-language) for the supported names and locale fields.

Use a separate administrator name that does not identify a system account.
The renderer rejects reserved names such as `root` and `operator`.

The bootloader starts the installed operating system.
Its password protects changes to boot commands.

Create the bootloader password digest with Podman on the build host.
The command uses the official Rocky Linux 10 image.
It installs `grub2-tools-minimal` inside a disposable container.
The command requires network access to fetch the image and package.

```sh
podman run --rm -it docker.io/rockylinux/rockylinux:10 \
  bash -c 'dnf -y --setopt=install_weak_deps=False install grub2-tools-minimal &&
           exec grub2-mkpasswd-pbkdf2 --iteration-count=100000'
```

Enter the password twice when the utility prompts.
The utility uses 100000 iterations to create the digest.

On a Rocky Linux host with `grub2-tools-minimal` installed, operate the utility directly.

```sh
grub2-mkpasswd-pbkdf2 --iteration-count=100000
```

Put the full resulting `grub.pbkdf2.sha512...` digest in `bootloader_password_hash` in `site.json`.
Use a unique password that differs from the account and disk passwords.
Keep that password in the approved recovery vault.

Set the recovery and central logging fields through [Site configuration](site.md).
These fields address selected CIS controls that require site decisions.
Central logging values can remain absent until deployment.
The security assessment requires completed logging configuration before release.

Do not copy the private SSH key into an image.
The private key permits access to systems that trust its public key.
Keep the private key in approved secure storage.

Select the whole installation disk before the next command.
The example selects `nvme0n1`.
The installer erases that disk and all its partitions.

```sh
python3 -m balboa render --flavor server --site site.json --disk nvme0n1 --output build/production-server
python3 -m balboa validate build/production-server/installation.ks --packages
python3 -m balboa iso build/production-server/installation.ks --output build/balboa-server.iso
```

The render step also creates three PNG images under the output directory in `branding/`.
Set `branding_text` in the site file to specify the name in the images.
See [Boot and desktop images](branding.md) for image locations and the command override.
Production renders enable Plymouth by default.
Use `--no-boot-splash` for a text boot without the Plymouth packages.

For workstations, replace `server` with `workstation`.
For laptops, replace `server` with `laptop`.
Use a new output directory for either flavor.
The renderer rejects an existing output directory that contains files.
The ISO command requires a successful offline DVD dependency test.

After a keyboard change, render a new Kickstart.
Build a new ISO from that Kickstart.
Previously generated images retain the previous keyboard configuration.

The disk parameter also accepts `disk/by-id/` identifiers.
Use a stable identifier when disk enumeration can change.
The installer can access only the selected disk through Kickstart storage commands.

Without a `luks_passphrase` site value, enter a unique LUKS2 passphrase through the local console during installation.
The default production Kickstart contains no disk passphrase.
At the end of installation, the installer uses `poweroff` to stop the system.

Start the installed system to apply the security profile.
After the automatic restart, unlock the disk again.
Use [the security procedure](security.md) before production release.

## Unattended disk encryption

A LUKS passphrase is an encryption secret for the disk.
Account and GRUB password digests do not supply this secret.
Set `luks_passphrase` in `site.json` to supply the installation key.

The value must contain the actual plaintext passphrase, with 5 to 128 printable characters.
The renderer rejects embedded line breaks and control characters.
Omit the field or use `null` to request interactive entry during installation.

Generate a new passphrase on the build host.

```sh
openssl rand -base64 48
```

Put the result in the `luks_passphrase` field.
Replace the placeholder in the example with the actual value.

```json
"luks_passphrase": "REPLACE_WITH_A_PLAINTEXT_LUKS_PASSPHRASE"
```

The renderer rejects this placeholder until you replace it.
Use JSON escaping for quotes or backslashes within the passphrase.
Use a unique passphrase for each production installation.
Retain the passphrase in the approved recovery vault.
Protect the site file with mode `0600`.
The renderer rejects group or other access to a site file that contains a LUKS passphrase.

Prepare the site file through the preceding procedure before these commands.
Before the image build, fetch the DVD source on the build host.

```sh
python3 -m balboa fetch --kind dvd
chmod 600 site.json
python3 -m balboa render --flavor laptop --kind dvd --site site.json --disk nvme0n1 --output build/laptop-unattended
python3 -m balboa iso build/laptop-unattended/installation.ks --kind dvd --output build/balboa-laptop-unattended.iso
```

The site JSON file, generated Kickstart, and ISO contain the plaintext passphrase.
Restrict these artifacts to the approved build and deployment accounts.
The ISO builder uses a private creation mask and sets the image mode to `0600`.

The manifest records `luks_passphrase_embedded` and `luks_passphrase_source` without the secret value.
The site value supplies the installation key only.
The installed system still requires disk unlock at each boot.

## DVD media

The DVD supplies all installation packages without network access.
The builder defaults to DVD media and rejects network boot media for installation.
Every ISO build resolves dependencies from the authenticated DVD with network access disabled.

```sh
python3 -m balboa fetch --kind dvd
python3 -m balboa render --flavor laptop --kind dvd --site site.json --disk nvme0n1 --output build/laptop-dvd
python3 -m balboa iso build/laptop-dvd/installation.ks --kind dvd --output build/balboa-laptop-dvd.iso
```

The DVD package collection differs from the online repositories.
Do an installation test of each selected DVD flavor.
Apply approved updates before release.
The locked DVD contains SCAP Security Guide 0.1.80 with a known account-shell assessment defect.
The defect can report a valid administrator shell as invalid.
The upstream correction changes how the assessment reads the final account entry in `/etc/passwd`. [Upstream correction](https://github.com/ComplianceAsCode/content/pull/14751)

After successful initial hardening, apply the approved security content update at the installed system console.
This command requires network access to the official Rocky repositories.
Retain the previous evidence before another assessment.

```sh
sudo dnf -y upgrade scap-security-guide openscap-scanner
```

Use [Updated security content](security.md#updated-security-content) for approved remediation after a security content update.
Updated security content can introduce new controls that require approved remediation before the assessment passes.
Review the changes through the site maintenance process.
Refresh the AIDE database through the same process.
The release test must pass with the updated content.

## Boot interfaces

The default Podman build preserves BIOS and UEFI optical boot structures.
It uses `mkksiso --skip-mkefiboot` because the container cannot mount the embedded firmware image.
UEFI boot from a USB device requires `--usb-uefi` or the native build mode.
Rootless Podman operates without host administrator privileges.

For UEFI USB media, use the rootless Podman build on the build host.

```sh
python3 -m balboa iso build/production-server/installation.ks --usb-uefi --output build/balboa-server-usb.iso
```

The tool container requires `mtools` for this mode.
If an older tool image lacks that package, rebuild it with `python3 -m balboa tools`.
The builder uses the official Lorax program and replaces its firmware image update procedure.

A FAT image contains the UEFI partition filesystem.
Mtools changes the GRUB configuration within a copy of the original FAT image without a mount.
The builder places that image in the appended UEFI partition.
The ISO test compares its configuration and signed boot programs with the ISO files.

For the alternative native mode, install Lorax on a Rocky Linux 10 build host.
Operate the native build command with administrator privileges on that host.
The native mode updates the embedded firmware image.

```sh
sudo python3 -m balboa iso build/production-server/installation.ks --native --output build/balboa-server-usb.iso
```

The native command also requires the Podman tool image for syntax tests.
The root Podman image store is separate from the user image store.
Prepare the tools under the same account that operates the native command.

The output manifest records whether the builder updated the UEFI USB image and which procedure it used.
The project does not change the signed Rocky boot programs.
Secure Boot still requires a separate firmware test.

## Artifact records

The ISO build creates a JSON manifest and a package list for the tools.
It also creates a `.dvd-packages.json` report for the offline package selection.
The manifest records the source digest, Kickstart digest, flavor, and security profile.
It also records the local tool image identity and source lock digest.
The `files_sha256` field identifies the files in `balboa-files/` and their permissions.
The installed system records its package list and datastream digest separately.

Generated Kickstart files contain account password digests and the public key.
Treat these files and images as restricted artifacts.
Lab artifacts contain disposable disk passphrases.
Production artifacts also contain a disk passphrase when the site file supplies `luks_passphrase`.
The ISO builder sets the image file mode to `0600`.

The build records support audits. Separate builds can produce different bytes.
The target installation uses fixed DVD package versions.
Online repositories for build tools and later installed system updates change over time.
For controlled releases, retain the tool package records, update records, and their repository metadata.

## Add custom files

The renderer creates `balboa-files/` beside `installation.ks`.
The directory contains scripts, configuration, and generated images as ordinary files.
Each path inside `balboa-files/` matches a path on the installed system.
For example, `balboa-files/etc/testfile.conf` becomes `/etc/testfile.conf`.

On the build host, enter these commands from the repository root.
Place your source file at `testfile.conf` before the second command.
The example selects `nvme0n1`. The installer erases that disk and all its partitions.

```sh
python3 -m balboa render --flavor laptop --site site.json --disk nvme0n1 --output build/laptop-files
install -D -m 0644 testfile.conf build/laptop-files/balboa-files/etc/testfile.conf
python3 -m balboa iso build/laptop-files/installation.ks --usb-uefi --output build/laptop-files.iso
```

After you render the Kickstart, add your files before you build the ISO.
The `-D` flag creates missing parent directories.
Set the desired permissions on each file before the ISO build.
Use a new render directory if your previous render lacks `balboa-files/`.

The installer copies regular files as root and preserves their permission bits.
It creates missing parent directories with mode `0755`.
It rejects symbolic links, special files, and files under `/dev`, `/proc`, `/run`, or `/sys`.
Use the actual directory if a target path contains a symbolic link.
The ISO builder compares file contents and permissions before it accepts the image.
The builder also compares the required hardening files with their project copies.

Kickstart copies the files before it applies the baseline configuration.
The baseline can change the files that it manages.
Anaconda records the copy step in `/root/balboa-files.log`.
See [Installation sequence](security.md#installation-sequence) for the steps that follow.

## References

These references describe the installation interfaces.
The review date is November 7, 2026.
The repository uses the RHEL10 Kickstart parser in Rocky Linux.

- [Kickstart commands for RHEL 10](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-commands-and-options-reference)
- [Lorax ISO customization](https://weldr.io/lorax/mkksiso.html)
- [Rocky Linux installation](https://docs.rockylinux.org/guides/installation/)
