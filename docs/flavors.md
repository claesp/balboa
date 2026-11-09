# Minimal flavors

Every flavor starts with mandatory packages from the `core` group.
The installer excludes weak dependencies and default group additions.
A weak dependency is an optional package relationship.
All flavors exclude the Postfix mail agent, Nautilus, and the QEMU guest agent.
The test workflow uses serial channels and does not require the QEMU guest agent.
The installed DNF configuration also disables weak dependencies and retains the flavor exclusions.

The common security tools support the required hardening and assessment workflow.
They include OpenSCAP, AIDE, audit, SELinux support, and the firewall.
They remain installed so that the operator can assess later changes.
The selected security content requires an rsyslog file permission rule even when journald supplies the logs.
The images retain that package but mask its service.
Only journald supplies active system logging.

## Server

The server adds OpenSSHD to the common minimum.
It excludes GNOME, wireless management, and Bluetooth services.
It also excludes printing and local service discovery.

The server does not install the general firmware bundle.
It also excludes graphics firmware and the Intel wireless firmware that the installer otherwise adds.
For physical hardware, add the firmware that the selected storage and network devices require.
QEMU uses virtual devices that do not require that firmware bundle.

After successful remediation, the server enables public key SSH access for the next boot.
The firewall permits the SSH service at that point.
The root account and password authentication remain disabled for SSH.

## Workstation

The workstation adds explicit packages for a minimal GNOME session.
It includes GDM, the desktop shell, the session manager, and the control center.
It also includes a terminal and key storage support.
It explicitly includes `pipewire-pulseaudio` and `alsa-ucm` for desktop audio.
DNF Automatic installs security updates after the first assessment.
The DNF configuration plugin controls package repositories.
The workstation includes Files (Nautilus) for file selection and search settings.
See [Desktop Settings](desktop-settings.md) for the file indexer and desktop defaults.

The workstation includes Intel and AMD graphics firmware.
It does not select the full workstation environment group.
It does not include an SSH server, wireless management, or Bluetooth services.

The package solver retains required libraries for GNOME panels.
A required library does not enable the corresponding hardware service.
The image includes Firefox with the project privacy policies.
It does not include office applications or printing services by default.

## Laptop

The laptop adds the same minimal GNOME session.
It uses the same DNF update and repository tools as the workstation.
It enables stable LVFS for firmware and the approved RPM sources after hardening.
See [Laptop package and firmware sources](package-sources.md#laptop-package-and-firmware-sources) for the source list and update procedure.
It also adds wireless networking, Bluetooth, device firmware, and power management.
The image includes `tuned-ppd` for GNOME power controls.
Explicit firmware packages support common Intel, Atheros, Broadcom, and Realtek wireless devices.
The laptop also includes Intel and AMD graphics firmware and Intel audio firmware.
It retains the general firmware package because that package supplies Intel Bluetooth firmware.

NetworkManager Bluetooth support requires the mobile networking stack in Rocky Linux 10.
The package solver retains that dependency chain.
The server flavor excludes those services.
Removing ModemManager breaks the required Bluetooth dependency chain.

The laptop does not include an SSH server by default.
The selected CIS profile can restrict wireless and Bluetooth operation.
Physical hardware tests and approved policy decisions remain necessary.

## Package review

The November 8 review removes the QEMU guest agent.
It also excludes NVIDIA firmware from the default Intel and AMD graphics selection.
The workstation excludes Intel wireless firmware because its role uses wired networking.

The laptop retains wireless firmware, Bluetooth dependencies, and power management.
The desktop keeps the control center, terminal, and secure credential storage.
Required GNOME libraries remain even when the corresponding optional service is absent.

The workstation and laptop use the DVD packages `dnf-automatic` and `dnf-plugins-core`.
They exclude GNOME Software, PackageKit, and Flatpak.
The server retains command-line package management through DNF.

The selected security policy still requires OpenSCAP, AIDE, audit, cryptsetup, and the logging packages.
The review retains these security requirements.
For NVIDIA hardware, define and test a separate package selection before installation.

Plymouth adds only its script theme, runtime dependencies, and font lookup support.
The Inter files come from the fixed project assets.
Use `--no-boot-splash` to omit Plymouth on a minimal server.

## Desktop updates

Use [Desktop package updates](updates.md) to manage automatic updates and package repositories.
The security update timer starts after initial hardening and the first assessment.
The operator controls restarts.

The workstation and laptop include official Rocky Firefox with locked privacy policies.
See [Firefox browser](browser.md) for the disabled features and policy location.
See [Maintenance](maintenance.md) for security assessments after approved updates.

## Package changes

Edit the package arrays in `flavors/` on the build host.
Use the `exclude` array for packages that the flavor must omit.
Do the dependency test before the next ISO build.

```sh
python3 -m balboa validate build/laptop/installation.ks --packages
```

The dependency test uses only BaseOS and AppStream from the authenticated DVD.
The test applies package exclusions and disables weak dependencies.
An unavailable package or unresolved dependency stops the ISO build and requires review.
See [Package sources](package-sources.md) for that review procedure.
See [Lenovo X1 Carbon Gen 13](lenovo-x1.md) for the laptop hardware findings.
