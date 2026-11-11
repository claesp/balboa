# Input devices and USB access

## Current image controls

The locked Rocky Linux 10.2 DVD contains USBGuard 1.1.4 and its rule parser.
The Balboa flavor definitions omit USBGuard.
The CIS Level 2 server and workstation profiles select rules that disable the USB storage driver and the Bluetooth service.
Both profiles leave the USBGuard rule group unselected.
These findings come from the security content on the locked DVD.

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

## Proposed USB policy

An allowlist permits only the devices that match its rules.
Use USBGuard to apply the allowlist to USB devices present at service startup and to devices connected later.
Block unmatched devices and restrict changes to the root account.
Keep logs of authorization decisions in the Linux audit log. [USBGuard daemon configuration](https://github.com/USBGuard/usbguard/blob/usbguard-1.1.4/usbguard-daemon.conf.in)

Use the vendor and product IDs to identify the model.
Use the serial number to identify a device when it reports a unique serial.
If a device has no unique serial, add its USBGuard hash and bind the rule to a tested USB port.
A USBGuard hash is a value calculated from data that the device reports.
Repeat the inventory after a restart to make sure that the chosen identifiers remain stable. [USBGuard rule language](https://usbguard.github.io/documentation/rule-language)

Match the full set of USB interfaces.
An interface is a function that a USB device exposes.
For example, one device can expose both a keyboard and a storage interface.
An exact match blocks a device that presents an extra interface.
Allow the approved hub and its required child devices when a dock exposes several USB devices. [USBGuard rule language](https://usbguard.github.io/documentation/rule-language)

A programmable USB device can copy the values that another device reports.
These rules control access by reported identity and port.
Device authentication against deliberate impersonation requires a separate cryptographic control. [Linux USB authorization](https://docs.kernel.org/usb/authorization.html)

## Proposed site configuration

This example proposes a `site.json` field for a later implementation.
An actual policy requires values from the intended device and host.

```json
{
  "usb_devices": {
    "keyboards": [
      {
        "id": "1234:5678",
        "serial": "EXAMPLE-001",
        "interfaces": ["03:01:01", "03:00:00"]
      }
    ],
    "audio": [],
    "storage": []
  }
}
```

The categories help administrators review the list.
Each generated rule uses the exact identity and interfaces for one approved device.
The proposed first policy leaves `storage` empty and retains the CIS USB storage rule.
A policy that permits USB storage can identify an approved disk by the same method.

USBGuard can list attached devices and generate candidate rules without starting the service.
If the reviewed USBGuard package is available on the inventory system, disconnect unrelated devices before you operate this command.
Review each candidate rule before you use it. [Red Hat USBGuard guidance](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/protecting-systems-against-intrusive-usb-devices)

```sh
sudo usbguard generate-policy
```

## Boot and other device types

USBGuard applies its rules after its service starts.
UEFI and the LUKS unlock prompt require separate boot tests.
For protection from kernel startup, Linux supports a default USB authorization setting.
Before you apply it, make sure that the approved unlock keyboard works during a cold boot. [Linux USB authorization](https://docs.kernel.org/usb/authorization.html)

USBGuard covers USB devices, including USB audio and storage.
Built-in input, audio, and storage can also use buses such as I²C, PCIe, or NVMe.
Bluetooth peripherals use Bluetooth pairing. A Bluetooth controller can itself use USB. [BlueZ device interface](https://bluez.readthedocs.io/en/latest/device-api/)
The platform controls Thunderbolt PCIe access through authorization and DMA protection. [Linux USB4 and Thunderbolt](https://docs.kernel.org/admin-guide/thunderbolt.html)

## Acceptance tests

1. Cold boot with only the built-in devices and unlock the disk.
2. Test the keyboard, touchpad, and TrackPoint at login.
3. Test the approved USB devices in their assigned ports and through their approved dock.
4. Connect an unapproved USB keyboard and disk. Use `sudo usbguard list-devices --blocked` to find both devices.
5. Restart, suspend, and resume. Repeat the authorization tests.
6. Make sure that the USBGuard policy records each decision in the audit log.
7. Make sure that an administrator can restore access with the approved recovery procedure.

The DVD rule parser accepts example rules for a keyboard with two interfaces and a device tied to a port.
These parser tests establish the rule syntax. Device tests require the physical X1 and its approved devices.
