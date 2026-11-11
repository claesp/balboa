# Input devices and USB access

## Current image controls

The locked Rocky Linux 10.2 DVD contains USBGuard 1.1.4 and its rule parser.
Balboa adds USBGuard and its SELinux policy when the site file includes `usb_devices`.
The CIS Level 2 server and workstation profiles select rules that disable the USB storage driver and the Bluetooth service.
Both profiles leave the USBGuard rule group unselected.
Balboa enables USBGuard during installation when the site selects it.

The USB storage rule controls the driver for all USB disks.
The rule provides no per-device exception.
After OpenSCAP applies the rule, a USBGuard allow rule alone cannot make a USB disk usable.
To allow a specific USB disk, change the CIS rule selection and record that difference in the assessment for that flavor.

## Inventory the installed system

Do this procedure on the installed X1 Carbon Gen 13 after initial hardening and restart.
Start with all removable devices disconnected.
Use the following commands to see the built-in devices and current controls.

```sh
cat /proc/bus/input/devices
lsblk --nodeps --output NAME,TRAN,TYPE,VENDOR,MODEL
rpm -q usbguard
systemctl is-enabled usbguard.service bluetooth.service
modprobe --showconfig | grep -E '^(blacklist|install)[[:space:]]+usb[-_]storage([[:space:]]|$)'
```

The first command shows the device names and their `eventN` identifiers.
Replace `event0` in the next command with the identifier for the keyboard, touchpad, or TrackPoint.
Read `ID_INPUT_*`, `ID_BUS`, and `ID_PATH` in the output when they are present.
Use `DEVPATH` to trace a device when `ID_BUS` is absent.

```sh
udevadm info --query=property --path=/sys/class/input/event0
```

The next command shows the USB path, vendor ID, product ID, and current authorization state.
A USB path identifies the port and any hubs above the device.
Operate the command once with only the built-in devices.
Connect each required external device or dock separately and repeat the command.

```sh
for device in /sys/bus/usb/devices/*; do
    [ -r "$device/idVendor" ] || continue
    printf '%s %s:%s authorized=%s\n' "${device##*/}" \
        "$(cat "$device/idVendor")" "$(cat "$device/idProduct")" \
        "$(cat "$device/authorized")"
done
```

Record which USB entries appear for each device or dock.
Include built-in devices that use USB, such as a USB camera or fingerprint reader, if present.
The USB and input inventory depends on the actual machine variant. [Lenovo hardware review](lenovo-x1.md#hardware-differences)

## USB policy

An allowlist permits only the devices that match its rules.
USBGuard applies the allowlist to USB devices present at service startup and to devices connected later.
It blocks unmatched devices and restricts policy changes to the root account.
It sends authorization decisions to the Linux audit log. [USBGuard daemon configuration](https://github.com/USBGuard/usbguard/blob/usbguard-1.1.4/usbguard-daemon.conf.in)

Use the exact USB vendor and product ID pair to identify an approved model.
A rule applies to all units that report that pair and the approved interfaces.
The same rule applies when you move a unit to another port or replace it with the same model.
Some hardware revisions or operating modes report a different pair or interface set.
Record a separate entry for each approved combination. [USBGuard rule language](https://usbguard.github.io/documentation/rule-language)

Match the full set of USB interfaces.
An interface is a function that a USB device exposes.
For example, one device can expose both a keyboard and a storage interface.
An exact match blocks a device that presents an extra interface.
Allow the approved hub and its required child devices when a dock exposes several USB devices. [USBGuard rule language](https://usbguard.github.io/documentation/rule-language)

A programmable USB device can copy the values that another device reports.
Two products with the same ID pair and interfaces also match the same rule.
Device authentication against deliberate impersonation requires a separate cryptographic control. [Linux USB authorization](https://docs.kernel.org/usb/authorization.html)

## Site configuration

Add the optional `usb_devices` object to your site file before you render the image.
Use the ID pair and interface codes from the approved model.
The following example shows a keyboard model with two interfaces.

```json
{
  "usb_devices": {
    "keyboards": [
      {
        "id": "1234:5678",
        "interfaces": ["03:01:01", "03:00:00"]
      }
    ],
    "audio": [],
    "storage": []
  }
}
```

Use `audio`, `cameras`, `hubs`, `keyboards`, `network`, `other`, `pointers`, or `storage` as category names.
The categories help administrators review the list. USBGuard matches the values in each entry.
Each allow rule uses the exact ID pair and interfaces for one approved model.
Omit `storage` or use an empty list for it.
The renderer rejects models with a mass-storage interface because the CIS profile disables USB storage.

An empty `usb_devices` object enables USBGuard and blocks all USB peripherals.
If you omit `usb_devices`, the image uses the default package selection and the CIS driver rules.

The keyboard entry corresponds to this USBGuard rule.

```text
allow id 1234:5678 with-interface equals { 03:00:00 03:01:01 }
```

The render directory contains the rule file at `balboa-files/etc/usbguard/rules.conf`.
The render and ISO manifests record its digest as `usbguard_rules_sha256`.
To change the image policy, edit the site file and render again. [Build and installation](build.md)

USBGuard can list attached devices and generate candidate rules without starting the service.
If the reviewed USBGuard package is available on the inventory system, disconnect unrelated devices before you operate this command.
Record only the ID pair and interfaces for each approved model. [Red Hat USBGuard guidance](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/protecting-systems-against-intrusive-usb-devices)

```sh
sudo usbguard generate-policy
```

## Boot and other device types

USBGuard applies its rules after its service starts.
UEFI and the LUKS unlock prompt require separate boot tests.
USBGuard starts after the installed system unlocks its root disk. [Linux USB authorization](https://docs.kernel.org/usb/authorization.html)

If the allowlist blocks your only input device, use the GRUB administrator password to edit the boot entry for one boot.
Add `systemd.mask=usbguard.service` to the kernel command line.
After login, correct `/etc/usbguard/rules.conf` as root.
Restart to apply the corrected rules. [systemd boot configuration](https://www.freedesktop.org/software/systemd/man/latest/systemd-debug-generator.html)

USBGuard covers USB devices, including USB audio and storage.
Built-in input, audio, and storage can also use buses such as I²C, PCIe, or NVMe.
Bluetooth peripherals use Bluetooth pairing. A Bluetooth controller can itself use USB. [BlueZ device interface](https://bluez.readthedocs.io/en/latest/device-api/)
The platform controls Thunderbolt PCIe access through authorization and DMA protection. [Linux USB4 and Thunderbolt](https://docs.kernel.org/admin-guide/thunderbolt.html)

## Acceptance tests

1. Cold boot with only the built-in devices and unlock the disk.
2. Test the keyboard, touchpad, and TrackPoint at login.
3. Test two units of each approved model across the ports and docks that users need.
4. Connect an unapproved USB keyboard and disk. Use `sudo usbguard list-devices --blocked` to find both devices.
5. Restart, suspend, and resume. Repeat the authorization tests.
6. Make sure that the USBGuard policy records each decision in the audit log.
7. Make sure that an administrator can restore access with the approved recovery procedure.

The DVD rule parser accepts the model rule for the keyboard with two interfaces.
These parser tests establish the rule syntax. Device tests require the physical X1 and its approved devices.
