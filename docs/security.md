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
The installed profiles inherit these base profiles through a tailoring file.
A tailoring file records explicit changes to a security profile.

The installed system uses `ssg-rl10-ds.xml`.
A datastream is a file that contains security assessment rules.
Balboa rejects reports with fewer than 100 applicable rules.

Balboa rejects reports without a passing rule.
This requirement prevents an empty assessment from passing.
The project does not substitute a RHEL datastream when Rocky content is absent.

## Policy differences

The packaged Rocky datastream contains a rule that expects Red Hat signing keys.
Balboa replaces `ensure_redhat_gpgkey_installed` with a native Rocky signing-key assessment.
That assessment requires the pinned Rocky fingerprint in both the key file and RPM database.

Sequoia reads the key formats that Rocky Linux 10.2 supplies.
The source lock also lists the permitted fingerprints for the distribution key bundle.
The native assessment rejects additional keys outside that list.
On first boot, the system imports only the approved key bundle after the fingerprint assessment.

Balboa also excludes `package_postfix_installed` to obey the requested minimal package scope.
All flavors forbid the Postfix package through a separate package assessment.
This mail agent exclusion is a declared policy deviation that requires review before release.

The tailoring file keeps the remaining selected CIS rules enabled.
The ISO manifest records both profile differences.
The reports include the native assessments before remediation, after remediation, and after restart.

These images use profiles based on CIS Level 2 with declared differences.
They do not claim conformance to an unmodified CIS profile.
The security owner must examine the differences against the applicable Rocky benchmark.

## Installed controls

All flavors use the same storage and account controls.
LUKS2 encrypts the volume that contains the system and swap.
The firmware and boot partitions remain unencrypted.

Separate filesystems contain `/home`, `/tmp`, `/var`, `/var/tmp`, `/var/log`, and `/var/log/audit`.
Temporary filesystems reject direct program execution through the `noexec` mount flag.

Each image requires a root console password digest.
The selected recovery policy requires this password for local recovery.
The renderer rejects an absent or malformed root digest.
The root console and administrator password fields can contain the same digest.
SSH rejects root login.

GRUB requires a password for changes to boot commands.
The site file supplies its PBKDF2 password digest.
Normal boot does not require that password.

The administrator account requires a password for sudo.
Sudo permits an authorized user to do administrator commands.
The repository contains no production passwords or private keys.

SELinux operates in enforcing mode.
Audit rules record account changes and administrator policy changes.
The initial firewall uses the `drop` zone.

The installer disables sshd.
The server enables public key SSH access after successful remediation.
SSH configuration permits public key authentication and rejects root login.

GNOME locks the workstation and laptop after 15 minutes without user activity.
The laptop includes wireless firmware and power management packages.
Rocky Linux 10 uses `tuned-ppd` for the GNOME power interface.
The selected CIS profile can disable wireless interfaces.

## Installation sequence

The installer applies the common controls through `%post`.
On first boot, the system applies the selected OpenSCAP remediation.
Remediation is an automatic change that addresses a security rule.

The system initializes the AIDE database after remediation.
AIDE records file contents for later comparison.
The system then requests a restart.

The AIDE baseline includes the completed SSH and firewall configuration.
The AIDE baseline excludes the changing assessment files under `/var/lib/balboa/`.
AIDE still covers the security programs and their configuration.

After restart, the system does an assessment without remediation.
The assessment retains XML results and an HTML report.
The system records its packages and the datastream digest.

The assessment fails if a rule fails, reports an unknown result, reports an error, or lacks a test.
The assessment also fails if it contains a fixed rule without a subsequent assessment.
The remediation stage permits unresolved findings but rejects scanner errors.
The remediation marker does not indicate conformance.

Server SSH can operate while the release assessment reports findings.
Restrict staging access until the security owner accepts the release evidence.
The administrator can use the local console to examine results.
The administrator controls each later firewall change.

The images use persistent journald logs and mask the rsyslog service.
The installer keeps the rsyslog package because the selected content requires its file permission configuration.
The images apply that configuration without an active rsyslog daemon.

The images mask the journal receiver service and socket.
Central logging uses the journal upload service with HTTPS.
The site supplies its receiver address and certificate paths.
See [Site configuration](site.md) for recovery and logging inputs.

Without a receiver configuration, the final assessment reports the missing upload service.
The automatic assessment does not prove that the remote receiver retains each event.
The site must test delivery and retention before release.

## Release conditions

Before release, do the following tasks for each flavor and hardware class.

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

The production layout uses a fixed 128 GB budget.
The default QEMU procedure uses a 32 GB disk with the same filesystem scheme.
The fixed log sizes require a capacity review for production workloads.

## Laptop decisions

The review records the selected Lenovo platform and the physical tests that it requires. [X1 Carbon Gen 13 review](lenovo-x1.md)

CIS Level 2 can conflict with wireless access and removable media.
The laptop flavor does not silently remove those controls.
The security owner must review each conflict before deployment.

If a deviation is necessary, create a separate reviewed security profile.
Keep the original profile assessment as evidence of the deviation.
Do not describe a modified profile as full CIS Level 2 conformance.

Suspend, resume, docking, camera access, and wireless operation require physical hardware tests.
The default swap allocation cannot support hibernation.
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
The default production procedure requests the passphrase at installation.
For unattended installation, the optional `luks_passphrase` site field supplies the plaintext encryption key.

The site JSON file, Kickstart, and ISO then contain that key.
Restrict access to these artifacts because they contain the plaintext installation key.
Do not put passphrases in kernel arguments.

## Updated security content

Updated security content can add controls that require changes before the next assessment passes.
The DVD policy still applies only to installation and initial hardening.
Do not remove the `remediated` marker after package updates.
Initial hardening rejects installed package versions outside the DVD inventory.

Retain the previous evidence before this procedure.
Review the updated controls.
Approve their remediation through the site maintenance process.
After the approved security content update, operate the following commands at the installed system console.

```sh
sudo bash <<'SH'
set -euo pipefail
source /etc/balboa/image.conf
out=/var/lib/balboa/evidence
scan=0
(umask 022; oscap xccdf eval --remediate \
    --tailoring-file /etc/balboa/tailoring.xml --profile "$PROFILE" \
    --results "$out/remediation-updated.xml" --report "$out/remediation-updated.html" \
    /usr/share/xml/scap/ssg/content/ssg-rl10-ds.xml) || scan=$?
[[ "$scan" == 0 || "$scan" == 2 ]]
if [[ "$DESKTOP" == yes ]]; then
    find /etc/dconf/db -maxdepth 1 -type f -exec chmod 0644 {} +
fi
python3 /usr/local/libexec/balboa/native_checks.py > "$out/native-after-update.json"
SH
```

The OpenSCAP command accepts status 2 because remediation can require another assessment or restart.
The desktop command retains readable dconf databases after remediation.
Examine the updated remediation report before the next commands.

After the site approves the resulting changes, refresh the AIDE database at the installed system console.

```sh
sudo aide --init
sudo mv /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz
```

The refreshed database accepts the current files as the integrity baseline.
Do not accept unexplained file changes through this step.
Do the assessment again through [Operation and recovery](#operation-and-recovery).
Require a passing assessment before release.

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
