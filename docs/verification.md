# Verification record

The initial test session covered November 7 and November 8, 2026.
The build host used x86_64 Linux with QEMU, Podman, and KVM.
The tests used authenticated Rocky Linux 10.2 boot and DVD media.

## Completed tests

The local suite contains 59 passing tests.
It includes site input restrictions, report assessment, guest archive restrictions, and expected OpenSCAP exit handling.
The suite also tests the serial unlock procedure and installer error detection.
The local suite accepts matching root console and administrator password digests for all three flavors.
Six launcher tests cover disk preservation, manifest constraints, boot reuse, and private UEFI variable files.

Keyboard tests reject `sv` and `se-latin1` when the input requires an XKB layout identifier.
The Swedish layout `se` renders correctly for all three flavors.
The Rocky container preflight accepts `se` and rejects `sv` before ISO creation.

Encryption tests cover site JSON passphrases, quoted characters, file permissions, and rejected control characters.
The tests require the passphrase to remain absent from manifests and console output.
The LUKS boundary tests accept five characters and reject four characters.
The image tests assess literal text, generated PNG dimensions, manifest digests, and embedded bytes.

All three flavors pass the RHEL10 Kickstart parser.
All guest shell programs pass Bash syntax tests.
The systemd service definitions pass inspection with their executable paths present.
The minimal post-installation script passes the disposable container test for all three flavors.

All three flavors pass the package availability test against official BaseOS and AppStream repositories.
The ISO tests accept the embedded Kickstart contents for all three flavors.
The tests also accept the BIOS and UEFI optical boot structures.

The earlier acceptance images complete installation on fixed 32 GB encrypted LVM disks.
The server and laptop complete BIOS installation.
The workstation completes UEFI installation.

Each installer reports the completion marker after its post-installation scripts.
The scripts use a separate administrator identity and explicit audit and SELinux dependencies.

## Automatic assessment results

These results describe the earlier acceptance images under `build/acceptance/`.
Each image completed remediation and AIDE initialization.
Each system restarted automatically.
On the next boot, each system did an assessment without remediation.
The final results showed no failed, erroneous, unknown, or untested selected rules.

| Flavor | Firmware | Passing rules | Not applicable | Findings |
| --- | --- | --- | --- | --- |
| Server | BIOS | 420 | 17 | 0 |
| Workstation | UEFI | 429 | 3 | 0 |
| Laptop | BIOS | 429 | 3 | 0 |

These results apply to the tailored profiles in [Security policy](security.md).
The profiles contain two declared differences from the packaged base profiles.
The results do not claim certification or conformance to an unmodified benchmark.

All three final native assessments accept the pinned Rocky signing keys and package exclusions.
The native assessments also accept the private journal key ownership and mode.
All three host assessments accept the fixed disk size, encrypted LVM sources, and required mount restrictions.

The server reports an active SSH service after remediation.
Its final package list excludes the unwanted graphics and Intel wireless firmware.
All three systems report enforcing SELinux and zero failed systemd units.

All three journal upload services report an active state and a successful result.
The retained upload logs contain no upload errors.
The local TLS receiver retains events from all three hostnames.
It rejects connections that omit a client certificate.

The receiver offers HTTP/1.1 to avoid the observed systemd 257 HTTP/2 buffer error.
Private key access uses a restricted group because Rocky SELinux policy blocks the default systemd credential label.
The tests retain SELinux enforcement throughout both corrections.

The production policy requires a root console password.
Production log receiver values remain deployment-time configuration.
The lab images use disposable root passwords and a local authenticated receiver.

## Interactive launcher results

The interactive script passes QEMU device initialization for BIOS and UEFI.
Each firmware mode accepts the `vda`, `sda`, and `nvme0n1` disk devices.
The startup tests use the laptop DVD ISO and temporary disks.
The tests pause the guest CPUs and operate without a window.

These startup tests do not replace the full installation and security assessments recorded in this document.
The GTK window requires examination in a graphical host session.
See [Interactive QEMU tests](qemu.md) for the installation and later boot commands.

## Unattended 128 GB installation

The laptop DVD completes installation on a 128 GB NVMe disk with UEFI.
The recorded test uses revision `51f764f` with disposable credentials and its former passphrase-file input.
The `luks_passphrase` site field reproduces the tested storage commands.
The keyboard layout is Swedish `se`.

The guest disk is `nvme0n1` and contains exactly 128000000000 bytes.
Anaconda marks Installation Destination as completed before partition creation.
The installer creates EFI and boot partitions, an encrypted physical volume, and all eight specified logical volumes.

The installer requests no LUKS setup passphrase.
Its post-installation programs report `BALBOA_INSTALL_COMPLETE`.
The machine then powers off.
The fixed 128 GB allocation requires no size correction.

This test uses the official DVD kernel and initrd with serial console arguments.
It covers installation and storage preparation.
The completed CIS assessment results remain those from the 32 GB tests.

The private test artifacts remain under `build/luks-storage-check/`.
The serial log is `vm-nvme-uefi/install.log` under that directory.
The file `installation-summary.json` records the result without the passphrase.

The following SHA256 digest identifies the disposable DVD ISO.

```text
76a95dc318565c1a8be67419b02e4949802ee513384c8a5aab3ce05444af5d04
```

## Content identity

The tool image contains `scap-security-guide-0.1.82-2.el10_2.rocky.1.1`.
The tool image contains OpenSCAP version 1.4.4.
The datastream contains both selected CIS Level 2 profile titles.

The repository records the official media identities in `sources.lock.json`.
Each built ISO has a separate manifest and package record.
Each installed assessment records its own content digest and package list.

The implementation revision is `f9bc899`.
These earlier images precede the generated branding assets.
All three assessments use the datastream with the following SHA256 digest.

```text
4985708fcfe92ff3a4ddb88ac1d6a9a3ec887c545032d7a7d592669670917213
```

The table shows the SHA256 digest for each disposable ISO from this session.

| Flavor | ISO digest |
| --- | --- |
| Server | `94e87b0dca74b73e7eef866766664320d69fa25317076eb82ff5dadb81d41486` |
| Workstation | `9d54f817020df5980b7d4d77296b3cf9eacc33e7f59ec907378b7f424e85a184` |
| Laptop | `189ce0fbe0ecc00e08f89f450a46d6f0f3c0104112cbfe4a8aaf6af3e118d075` |

## Local artifacts

The earlier acceptance ISO files use `build/balboa-FLAVOR-acceptance-lab.iso`.
Replace `FLAVOR` with `server`, `workstation`, or `laptop`.
Each ISO has a matching JSON manifest and tool package list.

The generated Kickstart files and disposable secrets remain under `build/acceptance/FLAVOR/`.
The collected results use the following directories.

- `build/acceptance/vm-server-bios/collected/evidence/`
- `build/acceptance/vm-workstation-uefi/collected/evidence/`
- `build/acceptance/vm-laptop-bios/collected/evidence/`

Each directory contains the HTML report, XML results, native assessments, and system records.
The collector journals remain under `build/lab-logging/logs/`.
The test session stops the collector after all final assessments pass.

Git excludes generated images, reports, and disposable credentials.
Retain release evidence in the approved artifact store.
Lab certificates expire after two days.
Create a new collector directory and new lab media for later test sessions.

## Remaining release evidence

Full CIS conformance requires the release procedure in [Security policy](security.md).
Passing automatic assessments do not cover every manual or organizational control.
The full CIS assessment tests use 32 GB disks.
The local suite tests the 128 GB allocation calculation and fixed sizes.
Production media still requires tests with actual site credentials and deployed logging configuration.

The remaining DVD flavor and firmware combinations require separate installation tests.
UEFI USB boot and Secure Boot require separate tests.
Laptop wireless operation, suspend, resume, and docking require physical hardware tests.
Site controls require an approved benchmark review and retained evidence.

## Generated boot and desktop images

The November 8 image tests cover all three minimal flavors.
The renderer creates three PNG files with the selected text.
The manifest digests match the generated files and the embedded Kickstart bytes.

All three baseline container tests pass with the generated assets.
The workstation and laptop tests read the wallpaper and login values through GNOME.
The tests also require GDM to read the login image.

The branded laptop completes a DVD installation on a fixed 32 GB UEFI virtual disk.
One QEMU screenshot shows the generated boot image behind the installed GRUB menu.
Another screenshot shows the custom login banner with the text `Powered by Rocky Linux`.

A separate server test uses a five-character LUKS passphrase from site JSON.
The official Rocky DVD installer creates the encrypted LVM layout without an encryption setup prompt.
The installer completes its installation scripts and powers off.

The local evidence resides under `build/branding-test/`.
The test directories contain disposable credentials and remain outside version control.
The five-character test uses a separate small ISO for the rendered Kickstart and the official DVD for packages.

The initial DVD assessment records 425 passing controls and one account-shell finding.
The finding includes a trailing line break in the final administrator shell path.
It matches the [known security content defect](https://github.com/ComplianceAsCode/content/pull/14751).
The original report remains in `collected-dvd-original/evidence/` under the laptop VM directory.

The test VM receives security content updates through the official Rocky repositories.
The updated packages are `scap-security-guide-0.1.82-2.el10_2.rocky.1.1` and `openscap-scanner-1.4.4-1.el10_2`.
The GNOME session shows the generated default wallpaper after login.
The installed image digests match the render manifest after hardening.

After the content update, the branded laptop completes remediation and a fresh assessment after restart.
The assessment records 429 passing controls, three not applicable controls, and no findings.
The native Rocky tests, encrypted LVM tests, and package boundary tests pass.

The final system reports enforcing SELinux and zero failed systemd units.
The authenticated journal upload service reports an active state and a successful result.
The test session stops its temporary receiver after assessment.

The updated results reside in `build/branding-test/vm-laptop-uefi/collected/evidence/`.
The boot, login, and desktop screenshots remain in that VM directory.
The branding implementation revision is `6368828`.

The following SHA256 digest identifies the branded laptop DVD ISO.

```text
8241deb0ca20d5cc6c09084ef9223b188f518cec116c1fbcf38397f4771c4d3e
```

## Photo, Inter, and graphical startup

The November 8 revision uses a fixed Unsplash mountain photo and the official Inter 4.1 font.
The renderer creates 1920 × 1080 boot, 2560 × 1440 wallpaper, and 640 × 180 login images.
It also creates an Inter bitmap font for GRUB.
Source digests and licenses reside under `assets/`.

All 46 local tests pass.
The tests cover source digests, image dimensions, splash defaults, and the restriction on automatic graphical unlock.
They also assess the journal generator with a representative vendor unit.
The generator removes network readiness dependencies and preserves other dependencies and service restrictions.

All three final Kickstart files pass the Rocky parser and package solver.
The solver resolves 306 server packages, 557 workstation packages, and 591 laptop packages.
These totals describe the selected installation packages and their dependencies.
The installed system also contains packages that the installer adds.

All three final installation scripts pass the disposable Podman test.
The tests include Inter discovery, GNOME defaults, Plymouth selection, and the final generator installation.
All guest shell programs pass syntax tests.

A fresh 32 GB UEFI server installation completes with the new photo and Plymouth base.
The final font lookup correction and journal generator receive separate tests on an isolated laptop snapshot.
These tests use the previous branded laptop as the snapshot source.
They do not replace a fresh installation test for every final flavor and firmware combination.

The QEMU GDM test shows the original photo banner and the exact `Powered by Rocky Linux` phrase.
The GNOME session shows the resized wallpaper and Inter text.
The early disk prompt shows readable Inter text and masked characters.
Esc switches to the text view, and captured startup frames show the animated spinner.

The first graphical prompt test exposed missing early font lookup support.
The final initramfs includes Inter, Fontconfig configuration, `fc-match`, and the packaged FreeType label renderer.
The tests retain SELinux enforcement throughout these changes.

The final laptop assessment records 429 passing controls, three not applicable controls, and no findings.
The native package tests and encrypted LVM assessment pass.
The system reports enforcing SELinux, zero failed units, and an active authenticated journal upload service.
The assessment includes the final journal generator and converted Inter font.

The final evidence resides under `build/plymouth-test/` and remains outside version control.
The package and installation records use the `final-FLAVOR-validation.log` and `final-FLAVOR-smoke.log` names.
The visual records reside in the `vm/` directory.
The final security reports reside in `vm/collected-generator-assessment/evidence/`.

## Startup measurements

The GRUB configuration reduces its menu wait from five seconds to two seconds.
The image disables repeated startup of the completed hardening service before AIDE initialization.
The journal generator removes the upload service dependency on network readiness.
The service retains its vendor restrictions and retries failed connections after 15 seconds.

An earlier ordinary boot records 3.625 seconds in userspace.
A graphical boot records 3.951 seconds in userspace before the disconnected-network test.
The graphical interface adds work in userspace.
The recorded userspace time was longer with the graphical interface.
Manual LUKS entry changes the early boot duration.
The tests therefore do not establish an improvement in total startup time.

With the virtual network link disconnected, the final image reaches its graphical target in 9.011 seconds of userspace time.
The previous dependency leaves the same offline test waiting for network readiness.
The final upload service waits between retries while GNOME remains available.
The offline test reports Inter for both GNOME and GDM and disables repeated hardening startup.

After the link returns, the upload service becomes active without a manual restart.
The local TLS receiver contains the event that the test writes while offline.
The collector binds only to `127.0.0.1:19532` on the build host.
The restored system reports zero failed units and enforcing SELinux.

## Transparent login banner

The later login revision removes the photo from `login.png` and retains the logo and both text lines.
The generated 640 × 180 PNG contains transparent background pixels and opaque content.
The existing image test now requires both types of pixels and a transparent corner.
All 46 local tests pass after this change.
The boot image and wallpaper match their previous generated bytes for the same text.

The new render resides in `build/transparent-login/laptop/`.
The earlier QEMU screenshots retain the photo banner from the previous revision.

## Generated file cleanup

The November 8 directory review retains all current project source files.
The review removes obsolete intermediate builds, old test ISOs, temporary helpers, and completed disposable test disks.
It recovers 33.94 GiB of allocated space.
The removal record resides in `build/cleanup-20261108/`.

The cleanup retains the current laptop DVD ISO, its render directory, and the active `build/qemu-laptop/` VM.
It also retains the official media cache, private site input, reports, manifests, and current previews.
The removed test disks and older ISO copies no longer support a new boot or installation from their former paths.
Their retained reports still describe the recorded historical assessments.

All 54 local tests pass.
Eight cleanup tests cover previews, explicit output selection, source protection, symbolic links, open files, and mounted directories.
The actual cleanup finds no open files among its obsolete output selection.
The preservation assessment accepts the retained inputs after removal.

## Desktop applications

The November 8 desktop revision adds GNOME Software, PackageKit, and official Rocky Firefox to the workstation and laptop.
The server package selection remains unchanged.
Both desktop selections resolve with weak dependencies disabled and their existing exclusions applied.
The official solver resolves 584 workstation packages and 618 laptop packages.

All 54 local tests pass after the renderer embeds the browser policy.
The renderer installs that policy only for desktop flavors.
The generated policy bytes match `guest/firefox-policies.json`.
The server output contains none of the three applications or the browser policy.

The Firefox runtime assessment passes with the DVD package version 140.10.2 and the repository package version 153.6.0.
The test reads the effective policy through a local automation connection in a disposable container.
Both versions accept every configured policy.
The assessed privacy preferences remain disabled and locked.
The policies also block Firefox studies.
Malware and phishing protection remain enabled.

Both final desktop Kickstart files pass the disposable installation script test.
The test reads the browser policy from the actual Kickstart instead of a separate source copy.
It accepts the GNOME Software PackageKit plugin and the live browser privacy assessment for each flavor.

These tests assess application packages and browser privacy enforcement.
They do not replace a full QEMU installation and CIS assessment of an ISO with the new desktop applications.
The recorded 429-control laptop assessment describes the earlier package selection.
Existing ISOs and the active user VM retain their previous contents.

The application test records reside under `build/desktop-apps/`.
The exact final Kickstart files reside in `final-workstation/` and `final-laptop/` under that directory.
The Firefox version assessments use `firefox-current.log` and `firefox-dvd.log`.

## DVD package policy and X1 review

The November 8 policy limits installation and initial hardening to the authenticated Rocky 10.2 DVD package versions.
Later approved official updates remain available.
The committed DVD inventory contains 5614 package identities.

All three final selections resolve from DVD metadata inside containers with network access disabled.
The server resolves 272 packages, the workstation resolves 583, and the laptop resolves 617.
The selection includes the explicit kernel and the desktop audio additions.
The preflight rejects a package absent from the DVD and an added network repository.

All 59 local tests pass.
The tests cover source defaults, inventory identity, exact package versions, repository restoration, and required initial provenance records.
The final laptop ISO passes embedded Kickstart and BIOS/UEFI boot structure tests.
It completes a fresh UEFI installation on the fixed 32 GB encrypted LVM test disk.

The first runtime test exposes a conflict between the earlier journal generator and DVD security remediation.
The final source removes that generator and retains the vendor journal unit.
A bounded NetworkManager startup wait replaces the generator workaround.
The service retains its vendor security directives and normal enabling behavior.

All three initial native reports accept every installed package version against the DVD inventory.
The reports also accept signing keys, package exclusions, and private key access permissions.
The system completes initial hardening before it restores the normal repository paths.

The original DVD content assessment reports 425 passes, three not-applicable results, and one account-shell finding.
That finding matches the known defect in SCAP Security Guide 0.1.80.
The test retains those original reports before any package update.

After initial hardening, the test installs approved official security content updates.
The installed versions are `scap-security-guide-0.1.82-2.el10_2.rocky.1.1` and `openscap-scanner-1.4.4-1.el10_2`.
The test applies the updated remediation and refreshes the AIDE database before another assessment.
The final assessment reports 429 passes, three not-applicable results, and no findings.
The native assessment and host storage assessment also pass.
SELinux remains enforcing, journal upload remains active, and the system reports zero failed units.

The final server and workstation installation script tests pass in disposable Podman containers.
The workstation test also accepts the live Firefox privacy policy and the GNOME Software PackageKit plugin.
The full laptop QEMU installation supplies the final laptop installation and hardening evidence.

A separate test receiver on port 19534 triggers an SELinux `name_connect` denial in the upload domain.
The test retains enforcement and changes the deployment endpoint to the standard journal port 19532.
The upload service then reports an active state.
The retained audit record identifies the denied port and domain.

With the virtual network link disconnected, the system reaches its graphical target in 8.045 seconds of userspace time.
The NetworkManager wait returns status 1, which the bounded wait configuration accepts without a failed unit.
The journal upload service retries through its vendor unit and retains its security directives.
SELinux remains enforcing, and the offline system reports zero failed units.
This test measures one virtual machine and does not establish physical laptop startup times.

The X1 Carbon Gen 13 review uses Lenovo specifications, Lenovo Linux support records, and Red Hat hardware records.
The DVD contains the reviewed Intel graphics, wireless, Bluetooth, and audio modules and firmware.
The image explicitly adds the missing PulseAudio-compatible service and ALSA UCM profiles.
Physical X1 acceptance remains pending in this record.
See [Lenovo X1 Carbon Gen 13](lenovo-x1.md) for device-specific limits and tests.

The test records reside under `build/dvd-policy/`.
The final laptop render is `laptop-final/`, and the final test VM directory is `vm-laptop-final/`.
The source reports use the `.dvd-packages.json` suffix.
The original DVD assessment resides in `vm-laptop-final/collected-dvd-original/evidence/`.
The updated assessment resides in `vm-laptop-final/collected-updated/evidence/`.
The offline boot record is `vm-laptop-final/console-offline.log`.

The regenerated inventory matches the committed inventory byte for byte.

The temporary log receiver stops after these tests.
The active user VM and its existing installation media retain their previous contents.

## CP69net X1 test image

The later production laptop build uses the private site input and the fixed 128 GB layout for `nvme0n1`.
The rootless UEFI USB builder updates the appended firmware partition without host administrator privileges.
Its configuration and signed program comparisons pass, and QEMU shows the USB installation menu.
See [CP69net X1 test image](cp69net-x1-build.md) for the artifact digest, build procedure, and installation behavior.

## Laptop package and firmware sources

The November 9 laptop test prepares the requested Rocky repositories, stable EPEL, and stable LVFS.
The EPEL release package signature matches the Rocky signing key.
The EPEL certificate fingerprint matches the Fedora publication.
The online metadata tests accept all requested Rocky RPM sources and the stable EPEL 10.2 catalog.

The QEMU test uses a disposable overlay of the previous laptop installation.
The test rejects the migration while the DVD repository restriction is active.
The staged RPM repositories become visible after the test releases that restriction.
The migration accepts the earlier policy format and gives the same result when operated again.

The later native assessment accepts the approved EPEL key.
The DVD-only native assessment rejects that key.
The firmware source list reports stable LVFS as enabled and LVFS testing as disabled.
The desktop account has an empty list of Flatpak remotes.
See [Laptop package and firmware sources](package-sources.md#laptop-package-and-firmware-sources) for the procedure.

## Name-only branding and rotating ring

The November 9 render uses the configured name in Inter Bold for the boot image, wallpaper, and transparent login banner.
The boot ring and disk prompt text use the same light color as the name.
The startup screen normally shows the name and ring.

All 60 local tests pass.
The production laptop Kickstart resolves 624 packages from the locked DVD without network access.
The generated images reside in `build/wordmark-x1/branding/`.

An offline QEMU overlay of the laptop test disk shows the new prompt, rotating ring, and login banner.
The disk prompt masks typed characters.
Esc switches to the text view.
The visual records reside in `build/wordmark-review/vm/`.

## Desktop security updates

The November 9 desktop selections replace GNOME Software and PackageKit with DNF Automatic and the DNF configuration plugin.
The offline dependency tests resolve 604 laptop packages, 566 workstation packages, and 272 server packages.
Both desktop selections omit GNOME Software, PackageKit, and Flatpak.
All 60 local tests and the laptop post-installation script test pass.

The QEMU migration retains GNOME, Firefox, and `fwupd` on the laptop.
The DNF configuration plugin disables EPEL and enables it again in that test.
The automatic service skips a run before the first assessment and while the DVD restriction is active.

The final test uses signed Rocky RPMs and Rocky advisory data on local media.
The service installs `libxslt-1.1.39-8.el10_2.1` for advisory `RLSA-2026:28584`.
The ordinary `libinput` update remains available for manual installation.
The test retains enforcing SELinux and records the transaction in the journal.
The test records reside in `build/desktop-updates-review/`.

## Custom files on the installation ISO

The November 11 test adds `etc/testfile.conf` to `balboa-files/` after the laptop render.
The ISO inspection finds the file on the media with its original contents and mode `0640`.
The Podman tests resolve the packages for all three flavors from the locked DVD without network access.
All 68 local tests pass. [Add custom files](build.md#add-custom-files)

QEMU completes two UEFI installations with the same laptop ISO.
One guest boots from virtual USB storage. The other guest boots from a virtual optical drive.
Anaconda finds the locked DVD by its volume label in both tests.
After boot, both guests contain the exact bytes at `/etc/testfile.conf`.
The file has mode `0640`, root ownership, and the SELinux type `etc_t` in both guests.
