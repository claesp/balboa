# Minimal flavors

Every flavor starts with mandatory packages from the `core` group.
The installer excludes weak dependencies and default group additions.
A weak dependency is an optional package relationship.
All flavors exclude the Postfix mail agent.

The common security tools support the required hardening and assessment workflow.
They include OpenSCAP, AIDE, audit, SELinux support, and the firewall.
They remain installed so that the operator can assess later changes.

## Server

The server adds OpenSSHD to the common minimum.
It excludes GNOME, wireless management, and Bluetooth services.
It also excludes printing and local service discovery.

The server does not install the general firmware bundle.
For physical hardware, add the firmware that the selected storage and network devices require.
QEMU uses virtual devices that do not require that firmware bundle.

After successful remediation, the server enables public key SSH access for the next boot.
The firewall permits the SSH service at that point.
The root account and password authentication remain disabled for SSH.

## Workstation

The workstation adds explicit packages for a minimal GNOME session.
It includes GDM, the desktop shell, the session manager, and the control center.
It also includes a terminal, file manager, and key storage support.

The workstation includes Intel and AMD graphics firmware.
It does not select the full workstation environment group.
It does not include an SSH server, wireless management, or Bluetooth services.

The package solver retains required libraries for GNOME panels.
A required library does not enable the corresponding hardware service.
The image does not include browsers, office applications, or printing services by default.

## Laptop

The laptop adds the same minimal GNOME session.
It also adds wireless networking, Bluetooth, device firmware, and power management.
The image includes `tuned-ppd` for GNOME power controls.
Explicit firmware packages support common Intel, Atheros, Broadcom, and Realtek wireless devices.
The laptop also includes Intel and AMD graphics firmware and Intel audio firmware.

NetworkManager Bluetooth support requires the mobile networking stack in Rocky Linux 10.
The package solver retains that dependency chain.
The server flavor excludes those services.

The laptop does not include an SSH server by default.
The selected CIS profile can restrict wireless and Bluetooth operation.
Physical hardware tests and approved policy decisions remain necessary.

## Package changes

Edit the package arrays in `flavors/` on the build host.
Use the `exclude` array for packages that the flavor must omit.
Do the dependency test before the next ISO build.

```sh
python3 -m balboa validate build/laptop/installation.ks --packages
```

The dependency test uses only official BaseOS and AppStream repositories.
The test applies package exclusions and disables weak dependencies.
An unresolved dependency prevents a boot ISO build.
