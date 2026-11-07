# Security policy

Balboa targets CIS Level 2 through Rocky OpenSCAP content.
Hardening is the reduction of system exposure to threats.
The project does not claim CIS certification or full conformance.

CIS publishes Rocky Linux 10 Benchmark version 1.0.0.
The packaged OpenSCAP profiles derive from the RHEL 10 benchmark.
These profiles are not substitutes for the Rocky benchmark review.

## Profile selection

The server uses `xccdf_org.ssgproject.content_profile_cis`.
The workstation and laptop use `xccdf_org.ssgproject.content_profile_cis_workstation_l2`.
The tool container requires both Level 2 profile titles.

The installed system uses `ssg-rl10-ds.xml`.
A datastream is a file that contains security assessment rules.
Balboa rejects reports with fewer than 100 applicable rules.

Balboa rejects reports without a passing rule.
This requirement prevents an empty assessment from passing.
The project does not substitute a RHEL datastream when Rocky content is absent.

## Installed controls

All flavors use the same storage and account controls.
LUKS2 encrypts the volume that contains the system and swap.
The firmware and boot partitions remain unencrypted.

Separate filesystems contain `/home`, `/tmp`, `/var`, `/var/tmp`, `/var/log`, and `/var/log/audit`.
Temporary filesystems reject direct program execution through the `noexec` mount flag.
The root account remains locked.

GRUB requires a password for changes to boot commands.
The site file supplies its PBKDF2 password digest.
Normal boot does not require that password.

The operator account requires a password for sudo.
Sudo permits an authorized user to do administrator commands.
The repository contains no production passwords or private keys.

SELinux operates in enforcing mode.
Audit rules record account changes and administrator policy changes.
The initial firewall uses the `drop` zone.

The images disable sshd at installation.
The images do not open inbound service ports.
SSH configuration permits public key authentication and rejects root login.

GNOME locks the workstation and laptop after 15 minutes without user activity.
The laptop includes wireless firmware and power management packages.
Rocky Linux 10 uses `tuned-ppd` for the GNOME power interface.
The selected CIS profile can disable wireless interfaces.

## Installation sequence

The installer applies the common controls through `%post`.
The first boot applies the selected OpenSCAP remediation.
Remediation is an automatic change that addresses a security rule.

The system initializes the AIDE database after remediation.
AIDE records file contents for later comparison.
The system then requests a restart.

After restart, the system does an assessment without remediation.
The assessment retains XML results and an HTML report.
The system records its packages and the datastream digest.

The assessment fails for failed, unknown, untested, erroneous, or unreassessed fixed rules.
The remediation stage permits unresolved findings but rejects scanner errors.
The remediation marker does not indicate conformance.

Balboa does not enable remote access after a failed assessment.
The administrator can use the local console to examine results.
The administrator controls each later firewall change.

## Release conditions

Before release, do these tasks for each flavor and hardware class:

1. Make sure that the installed system passes the automatic assessment.
2. Compare each selected rule with the applicable Rocky Linux CIS benchmark.
3. Examine all manual controls with the security owner.
4. Record approved deviations with an owner, reason, expiry date, and affected controls.
5. Make sure that disk encryption and boot protection operate on the target hardware.
6. Make sure that storage capacity and audit retention meet site requirements.
7. Make sure that backup restoration and administrator recovery operate correctly.
8. Record the image digest and the evidence location.

OpenSCAP does not cover all organizational controls.
Site decisions include time sources, remote logging, firmware protection, and physical access.
The operator must supply these decisions before release.

The generated partition layout requires at least 64 GiB.
The QEMU procedure uses an 80 GiB disk.
The fixed log sizes require a capacity review for production workloads.

## Laptop decisions

CIS Level 2 can conflict with wireless access and removable media.
The laptop flavor does not silently remove those controls.
The security owner must review each conflict before deployment.

If a deviation is necessary, create a separate reviewed security profile.
Keep the original profile assessment as evidence of the deviation.
Do not describe a modified profile as full CIS Level 2 conformance.

Suspend, resume, docking, camera access, and wireless operation require physical hardware tests.
Hibernation is not supported by the default swap allocation.
TPM enrollment and automatic disk unlock require a separate site design.

## Operation and recovery

Operate these commands at the installed system console.
The first command shows the services that apply and assess the policy.
The results remain under `/var/lib/balboa/evidence/`.

```sh
sudo systemctl status balboa-harden.service balboa-audit.service
sudo cat /var/lib/balboa/evidence/summary.json
sudo journalctl -u balboa-harden.service -u balboa-audit.service
```

If remediation fails, examine `harden.log` before another attempt.
Do not create the `remediated` marker manually.
An incorrect marker bypasses the remediation stage.

After approved corrections, do another assessment from the installed system console.
The command removes the assessment marker but retains prior report files until the service replaces them.
Copy the prior evidence to secure storage before the command.

```sh
sudo rm -f /var/lib/balboa/assessed
sudo systemctl restart balboa-audit.service
```

Use a unique passphrase for each production installation.
Keep recovery material in the approved site vault.
Do not put production passphrases in Kickstart files or kernel arguments.

## References

These sources describe the upstream security interfaces.
The review date is November 7, 2026.
Profile content can change when the installed package changes.

- [CIS Rocky Linux benchmarks](https://www.cisecurity.org/benchmark/rocky_linux)
- [RHEL 10 security changes](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/pdf/considerations_in_adopting_rhel_10/security)
- [OpenSCAP security content](https://www.open-scap.org/security-policies/scap-security-guide/)
- [Upstream server profile](https://github.com/ComplianceAsCode/content/blob/master/products/rhel10/profiles/cis.profile)
- [Upstream workstation profile](https://github.com/ComplianceAsCode/content/blob/master/products/rhel10/profiles/cis_workstation_l2.profile)
- [Rocky Linux 10 package changes](https://docs.rockylinux.org/latest/releases/release_notes/10_0/)
