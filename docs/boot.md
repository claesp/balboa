# Boot process

Production images use Plymouth for the graphical Linux boot.
Plymouth is a program that shows graphics during startup.
The normal lab mode retains a text boot for automatic serial unlock.

GRUB shows the generated photo before Linux starts.
Plymouth fits the full image to the screen so that the photo credit stays visible.
A rotating ring shows activity at the center of the screen.
The configured name sits above the ring.
The ring and the name use the same light color.

The encrypted disk prompt uses a dark entry field with light masked characters.
The prompt does not show the passphrase.
A spinner indicates activity and does not claim an exact completion percentage.

## Configuration

Use the optional `boot_splash` site field to select graphical or text startup.
The production default is `true`.
Use `false` for serial-only systems or a server without graphics.

Operate render commands from the repository root on the build host.
Use `--no-boot-splash` to override the site value and omit the Plymouth packages.
Use `--boot-splash` to enable graphics explicitly.

```sh
python3 -m balboa render --flavor laptop --site site.json --disk nvme0n1 --output build/laptop-graphical
python3 -m balboa render --flavor server --site site.json --disk sda --no-boot-splash --output build/server-text
```

The images use `rhgb` and `quiet` for the graphical boot.
The configuration hides routine console output and retains system logs.
The audit, encryption, SELinux, and security assessment controls remain active.

## QEMU tests

Use the interactive launcher for a graphical unlock test.
The automatic VM command requires the normal lab mode with serial output.
A graphical lab render requires manual disk unlock through the QEMU window.

```sh
python3 -m balboa render --flavor laptop --lab --boot-splash --output build/laptop-graphical-lab
python3 -m balboa iso build/laptop-graphical-lab/installation.ks --output build/laptop-graphical-lab.iso
python3 scripts/start-qemu.py --iso build/laptop-graphical-lab.iso --workdir build/qemu-graphical
```

After installation, boot the installed disk with the same VM directory.
Read the disposable passphrase from the restricted `lab-secrets.json` file at the local build host.
Enter that passphrase in the QEMU window.

```sh
python3 scripts/start-qemu.py --boot --workdir build/qemu-graphical
```

## Startup speed

The GRUB menu waits two seconds instead of five seconds.
GRUB skips discovery of other operating systems when it creates its configuration.
The fixed images do not require that discovery step.

The first boot still applies the full security policy and creates the AIDE database.
Initial hardening uses the installed DVD package versions and denies IP traffic from the hardening service.
See [Package sources](package-sources.md) for the initial repository restriction and later updates.
The next boot still assesses that policy after a restart.
These initial tasks take longer than an ordinary boot.

After successful remediation, the hardening service disables its automatic startup before AIDE initialization.
This avoids a network dependency from that service on later boots.
The audit service still performs its required assessment after restart.

NetworkManager waits at most five seconds for its startup attempt during boot.
An offline timeout completes that wait without a failed unit.
NetworkManager continues connection attempts after the wait.
The images use local storage and local account authentication.
Before adding remote mounts or network account services, review this bounded wait.

Journal upload retains its vendor unit and security directives.
Its service retries failed uploads after 15 seconds.
Persistent journald storage retains the local events while the receiver is unavailable.

The earlier journal unit generator is removed because generated units prevent normal service enabling during DVD security remediation.
The timeout drop-in changes only the network startup wait command and its result handling.
The [NetworkManager manual](https://networkmanager.dev/docs/api/latest/nm-online.html) describes the startup timeout.

The images retain the LUKS key derivation cost.
They retain the required security services and firmware support.
A quiet screen does not itself reduce startup time.

## Recovery and implementation

Press Esc to switch between the splash and the available boot messages.
If graphics fail, use a text-boot image or remove `rhgb` through the protected GRUB editor.
Retain the GRUB recovery password in the site recovery vault.

The Plymouth files reside in `/usr/share/plymouth/themes/balboa/`.
The installation script rebuilds the initramfs after theme selection.
An initramfs contains the programs that Linux needs before it mounts the system disk.

The early font setup includes Inter, `fc-match`, and its font configuration.
The packaged FreeType renderer uses that program to find its font.
The generated boot image remains separate from the passphrase and contains no credentials.

The [RHEL boot guide](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/interactively_installing_rhel_from_installation_media/troubleshooting-after-installation) describes the graphical boot switch.
The [Rocky Plymouth source package](https://dl.rockylinux.org/pub/rocky/10/AppStream/source/tree/Packages/p/plymouth-24.004.60-17.el10.src.rpm) supplies the packaged script interfaces.
See [Boot and desktop images](branding.md) for source assets, image sizes, and the Inter license.
