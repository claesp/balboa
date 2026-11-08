# Build and installation

The build host requires an x86_64 Linux system.
Podman supplies Rocky Linux tools in a separate environment.
QEMU supplies a virtual machine for installation tests.

The host requires these tools:

- Python 3.11 or later
- ImageMagick with SVG support and Fontconfig
- `grub2-mkfont` or `grub-mkfont` for the Inter boot font
- Curl and GnuPG
- Podman
- OpenSSL and OpenSSH tools
- QEMU system tools and `qemu-img`
- OVMF firmware for UEFI tests

Operate all repository commands from the repository root.
Reserve at least 8 GiB for a boot ISO and one server test.
Reserve more space for desktop tests and DVD images.

## Prepare the tools

The container base digest appears in `sources.lock.json`.
Package installation uses the official Rocky repositories.
The container build requires network access.

```sh
python3 -m balboa tools
python3 -m balboa fetch --kind boot
```

The source command requires a matching signature, signing key, and ISO digest.
The lock file fixes the media version.
The command retains the downloaded ISO for later builds.

## Create production media

Copy the site example on the build host.
The example contains placeholders that the renderer rejects.
The site file contains the administrator account information.

```sh
cp examples/site.json site.json
chmod 600 site.json
```

Create a password digest and an SSH key on the build host.
The first command prompts for the account password.
The second command prompts for the private key passphrase.

```sh
openssl passwd -6
ssh-keygen -t ed25519 -f ~/.ssh/balboa_operator
```

Put the password digest in `password_hash` in `site.json`.
Put the root console password digest in `root_password_hash` in `site.json`.
Both password fields can contain the same digest.
Retain the root password in the approved recovery vault.
Put the public key contents in `ssh_public_key` in `site.json`.
Set the hostname and local language fields in `site.json`.
Use an XKB layout identifier for `keyboard`, such as `se` for Swedish or `us` for US English.
See [Keyboard and language](site.md#keyboard-and-language) for the supported names and locale fields.
Use a separate administrator name that does not identify a system account.
The renderer rejects reserved names such as `root` and `operator`.

The bootloader starts the installed operating system.
Its password protects changes to boot commands.

Create the bootloader password digest with Podman on the build host.
The command uses the official Rocky Linux 10 image.
It installs `grub2-tools-minimal` inside a disposable container.
The command requires network access to obtain the image and package.

```sh
podman run --rm -it docker.io/rockylinux/rockylinux:10 \
  bash -c 'dnf -y --setopt=install_weak_deps=False install grub2-tools-minimal &&
           exec grub2-mkpasswd-pbkdf2 --iteration-count=100000'
```

Enter the password twice when the utility prompts.
The utility uses 100000 iterations to create the digest.

On a Rocky Linux host with `grub2-tools-minimal` installed, operate the utility directly:

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
python3 -m balboa validate build/production-server/installation.ks
python3 -m balboa iso build/production-server/installation.ks --output build/balboa-server.iso
```

The render step also creates three PNG images under the output directory in `branding/`.
Set `branding_text` in the site file to put your text below the logo.
See [Boot and desktop images](branding.md) for image locations and the command override.
Production renders enable Plymouth by default.
Use `--no-boot-splash` for a text boot without the Plymouth packages.

For workstations, replace `server` with `workstation` and use a new output directory.
For laptops, replace `server` with `laptop` and use a new output directory.
The renderer rejects an existing output directory that contains files.
The boot ISO command also requires a successful package availability test.
After a keyboard change, render a new Kickstart and rebuild the ISO.
Previously generated images retain the previous keyboard configuration.

The disk parameter also accepts `disk/by-id/` identifiers.
Use a stable identifier when disk enumeration can change.
The installer can access only the selected disk through Kickstart storage commands.

Without a `luks_passphrase` site value, enter a unique LUKS2 passphrase through the local console during installation.
The default production Kickstart contains no disk passphrase.
The installer stops after installation through the `poweroff` command.

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

Generate a new passphrase on the build host:

```sh
openssl rand -base64 48
```

Put the result in the `luks_passphrase` field.
Replace the example placeholder with the actual value:

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
Fetch the DVD source on the build host before the image build:

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

The DVD permits package installation without network access.
The Kickstart source type must match the source ISO type.
The ISO command rejects a manifest with a different source type.

```sh
python3 -m balboa fetch --kind dvd
python3 -m balboa render --flavor laptop --kind dvd --site site.json --disk nvme0n1 --output build/laptop-dvd
python3 -m balboa iso build/laptop-dvd/installation.ks --kind dvd --output build/balboa-laptop-dvd.iso
```

The DVD package collection can differ from the online repositories.
Do an installation test of each selected DVD flavor.
Apply approved updates before release.
The locked DVD contains SCAP Security Guide 0.1.80 with a known account-shell assessment defect.
The defect can report a valid administrator shell as invalid.
The [upstream correction](https://github.com/ComplianceAsCode/content/pull/14751) fixes the final account entry in `/etc/passwd`.

After a DVD installation, apply the approved security content update at the installed system console.
This command requires network access to the official Rocky repositories.
Retain the previous evidence before another assessment.

```sh
sudo dnf -y upgrade scap-security-guide openscap-scanner
```

Use [Operation and recovery](security.md#operation-and-recovery) to repeat the assessment after approved updates.
The release test must pass with the updated content.

## Boot interfaces

The default Podman build preserves BIOS and UEFI optical boot structures.
It uses `mkksiso --skip-mkefiboot` because the container cannot mount the embedded firmware image.
UEFI boot from a USB device requires the native build mode.

For a UEFI USB image, install Lorax on a Rocky Linux 10 build host.
Operate the native build command with administrator privileges on that host.
The native mode updates the embedded firmware image.

```sh
sudo python3 -m balboa iso build/production-server/installation.ks --native --output build/balboa-server-usb.iso
```

The native command also requires the Podman tool image for syntax tests.
The root Podman image store is separate from the user image store.
Prepare the tools under the same account that operates the native command.

The output manifest records whether the native mode updated the UEFI USB image.
The project does not change the signed Rocky boot programs.
Secure Boot still requires a separate firmware test.

## Artifact records

Each ISO has a JSON manifest and a package list for the tools.
The manifest records the source digest, Kickstart digest, flavor, and security profile.
It also records the local tool image identity and source lock digest.
The installed system records its package list and datastream digest separately.

Generated Kickstart files contain account password digests and the public key.
Treat these files and images as restricted artifacts.
Lab artifacts contain disposable disk passphrases.
Production artifacts also contain a disk passphrase when the site file supplies `luks_passphrase`.
The ISO builder sets the image file mode to `0600`.

The build is auditable but not byte reproducible.
Online package repositories change over time.
For controlled releases, use approved repository snapshots and retain their metadata.

## References

These references describe the installation interfaces.
The review date is November 7, 2026.
The repository uses the RHEL10 Kickstart parser in Rocky Linux.

- [Kickstart commands for RHEL 10](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/automatically_installing_rhel/kickstart-commands-and-options-reference)
- [Lorax ISO customization](https://weldr.io/lorax/mkksiso.html)
- [Rocky Linux installation](https://docs.rockylinux.org/guides/installation/)
