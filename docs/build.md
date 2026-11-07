# Build and installation

The build host requires an x86_64 Linux system.
Podman supplies Rocky Linux tools in a separate environment.
QEMU supplies a virtual machine for installation tests.

The host requires these tools:

- Python 3.11 or later
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
Put the public key contents in `ssh_public_key` in `site.json`.
Set the hostname and local language fields in `site.json`.
Use a separate administrator name that does not identify a system account.
The renderer rejects reserved names such as `root` and `operator`.

Create a bootloader password digest on a Rocky Linux host with `grub2-tools` installed.
The bootloader starts the installed operating system.
Its password protects changes to boot commands.

```sh
grub2-mkpasswd-pbkdf2
```

Put the resulting `grub.pbkdf2.sha512` digest in `bootloader_password_hash` in `site.json`.
Use a unique password that differs from the account and disk passwords.
Keep that password in the approved recovery vault.

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

For workstations, replace `server` with `workstation` and use a new output directory.
For laptops, replace `server` with `laptop` and use a new output directory.
The renderer rejects an existing output directory that contains files.
The boot ISO command also requires a successful package availability test.

The disk parameter also accepts `disk/by-id/` identifiers.
Use a stable identifier when disk enumeration can change.
The installer can access only the selected disk through Kickstart storage commands.

At installation, enter a unique LUKS2 passphrase through the local console.
The production Kickstart contains no disk passphrase.
The installer stops after installation through the `poweroff` command.

Start the installed system to apply the security profile.
After the automatic restart, unlock the disk again.
Use [the security procedure](security.md) before production release.

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

Generated Kickstart files contain the password digest and public key.
Treat these files and images as restricted artifacts.
Lab artifacts also contain disposable disk passphrases.

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
