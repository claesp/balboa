# Lenovo X1 Carbon Gen 13

The target hardware is the ThinkPad X1 Carbon Gen 13.
The review date is November 8, 2026.
The project does not yet contain physical acceptance evidence from this laptop.

Lenovo lists RHEL 10.0 support for its Lunar Lake and Arrow Lake variants.
The [Lenovo Linux matrix](https://support.lenovo.com/nz/en/solutions/pd031426/) identifies those operating system combinations.
Red Hat also lists [21NTZCKNCN](https://catalog.redhat.com/en/hardware/system/detail/281757) and [21NYZCUFCN](https://catalog.redhat.com/en/hardware/system/detail/287037) for RHEL 10.x.
These records support a compatibility assessment but do not certify this custom Rocky image.

## Hardware differences

The [Lenovo specifications](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_X1_Carbon_Gen_13/ThinkPad_X1_Carbon_Gen_13_Spec.pdf) list several hardware choices within this generation.
The V-series models use Lunar Lake, and the U-series and H-series models use Arrow Lake.
Wireless choices include Intel AX211 and BE201.
Camera choices include FHD and MIPI variants.
Record the exact machine type, processor, camera, and wireless identifiers before physical qualification.

Rocky Linux 10 requires x86-64-v3 support.
Use the [Rocky CPU procedure](https://docs.rockylinux.org/gemstones/test_cpu_compat/) on the actual laptop before installation.
The firmware mode for the laptop image is UEFI.

## DVD driver review

The locked DVD contains kernel `6.12.0-211.16.1.el10_2.0.1`.
Its `kernel-modules` package contains `xe`, `i915`, `iwlwifi`, `btintel`, and the Lunar Lake SOF audio module.
The Kickstart explicitly selects the kernel so that the package preflight also resolves its dependencies.

The laptop retains these DVD firmware packages:

| Package | Purpose for this hardware review |
| --- | --- |
| `linux-firmware` | Lunar Lake Xe graphics, Lenovo sensor hub files, and Intel Bluetooth firmware |
| `intel-gpu-firmware` | Intel i915 firmware |
| `iwlwifi-mvm-firmware` | Intel wireless firmware, including the BE201 `bz-b0` family |
| `alsa-sof-firmware` | Intel SOF audio firmware and topology files |
| `intel-audio-firmware` | Additional Intel audio firmware |

The DVD includes `xe/lnl_guc_70.bin.xz` and `LENOVO/ish/ish_lnlm_lenovo_X1_2025_5.8.4.7720.bin.xz` in `linux-firmware`.
Removing that package removes firmware that this platform can require.
Package presence establishes availability but does not prove operation on each device revision.

Intel documents BE201 support in its [Linux wireless release notes](https://downloadmirror.intel.com/842132/ReleaseNotes_WiFi_LinuxCore89.pdf).
Use the distribution kernel and its matching DVD firmware for the initial test.
Do not replace individual firmware files or install another kernel without the package source review.

## Audio changes

The previous minimal desktop selection includes PipeWire and WirePlumber but omits the PulseAudio-compatible service and ALSA device profiles.
The workstation and laptop now explicitly install `pipewire-pulseaudio` and `alsa-ucm` from the DVD.
The server omits these desktop packages.

UCM means Use Case Manager for ALSA device configuration.
The [PipeWire manual](https://docs.pipewire.org/page_man_pipewire-pulse_1.html) describes its PulseAudio-compatible service.
[WirePlumber](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/alsa.html) uses available UCM profiles to configure sound devices.
Do tests of the speakers, internal microphone, headset jack, and Bluetooth audio on the actual laptop.

## Features for separate review

The MIPI camera requires a matching sensor and image processing stack.
The image does not declare complete support for that camera variant.
Inspect the actual device identifiers before any camera driver decision.
An external UVC camera provides a separate test path when the internal camera lacks support.

Thunderbolt docks can require `bolt` for device authorization.
The DVD contains `bolt`, but the default minimal image does not add a dock authorization service without a dock requirement.
Keep firmware DMA protection active.
Do tests of the selected dock and external displays.

The DVD also contains `fprintd`, `libfprint`, `iio-sensor-proxy`, and `libcamera`.
These optional packages are not automatic additions to the image.
Fingerprint authentication requires a supported sensor and a review of the authentication policy.
Firmware payloads outside the DVD require the site firmware review process.
The laptop uses `fwupd` with the stable LVFS remote for firmware discovery.
See [Laptop package and firmware sources](package-sources.md#laptop-package-and-firmware-sources) for the remote configuration.

Optional cellular modems, presence detection, and privacy screen behavior require separate hardware tests.
Lenovo notes Linux feature limits in its [product specifications](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_X1_Carbon_Gen_13/ThinkPad_X1_Carbon_Gen_13_Spec.pdf).
The [Linux user guide](https://download.lenovo.com/pccbbs/mobiles_pdf/x1_carbon_gen13_2in1_gen10_linux_ug.pdf) describes the platform controls.

## Security and power

The selected CIS profile can restrict wireless networking, Bluetooth, USB access, and sleep behavior.
The hardware review does not remove these security controls.
Use an approved laptop policy decision before changes to those restrictions.

Use a wired USB-C adapter when the approved policy prevents wireless access.
Do tests of disk unlock, lid close, suspend, resume, battery drain, and power profiles after hardening.
The image includes `tuned` and `tuned-ppd` for power management.
The default disk layout does not support hibernation.

Use the firmware sleep modes that the actual model supplies.
Lenovo describes suspend-to-idle behavior in its [power configuration reference](https://docs.lenovocdrt.com/ref/bios/settings/thinkpad/power/).
Do not force an unsupported sleep state through a generic kernel parameter.

## Physical acceptance

Before a production release, record these results on the actual X1 Carbon Gen 13:

1. Record the machine type, BIOS version, processor, and device identifiers.
2. Install the DVD image in UEFI mode on the selected NVMe disk.
3. Make sure that the fixed encrypted LVM layout and graphical unlock operate correctly.
4. Assess the selected CIS profile and examine any wireless or sleep restrictions.
5. Do tests of graphics, brightness controls, external displays, keyboard, touchpad, and TrackPoint.
6. Do tests of the required network, Bluetooth, audio, camera, and dock configurations.
7. Do tests of suspend and resume on AC power and battery power.
8. Retain the reports and review any missing drivers through [Package sources](package-sources.md).

QEMU tests supply installation evidence for virtual devices.
They do not replace these physical device tests.
Secure Boot requires a separate firmware acceptance test with the actual installation medium.
