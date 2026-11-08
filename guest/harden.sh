#!/bin/bash
set -euo pipefail
umask 077
source /etc/balboa/image.conf
state=/var/lib/balboa
out=$state/evidence
install -d -m 0700 "$out"
exec >> "$out/harden.log" 2>&1
source /usr/local/libexec/balboa/failure.sh
python3 /usr/local/libexec/balboa/package_source.py guard
if [[ "$DESKTOP" == yes ]]; then
    systemctl mask --runtime --now packagekit.service
fi
ds=/usr/share/xml/scap/ssg/content/ssg-rl10-ds.xml
test -f "$ds"
oscap info --profiles "$ds" | grep -F "${BASE_PROFILE}:"
python3 /usr/local/libexec/balboa/native_checks.py --install-keys --dvd-only > "$out/native-before.json"
rpm -qa | sort > "$out/packages.txt"
sha256sum "$ds" > "$out/datastream.sha256"
cp /etc/balboa/image.conf "$out/image.conf"
oscap info "$ds" > "$out/content.txt"
rc=0
(
umask 022
oscap xccdf eval --remediate --tailoring-file /etc/balboa/tailoring.xml --profile "$PROFILE" \
    --results "$out/remediation.xml" --results-arf "$out/remediation-arf.xml" \
    --report "$out/remediation.html" "$ds"
) || rc=$?
[[ "$rc" == 0 || "$rc" == 2 ]]
python3 /usr/local/libexec/balboa/result_gate.py "$out/remediation.xml" \
    --profile "$PROFILE" --allow-findings > "$out/remediation-summary.json"
python3 /usr/local/libexec/balboa/native_checks.py --dvd-only > "$out/native-after.json"
if [[ "$DESKTOP" == yes ]]; then
    find /etc/dconf/db -maxdepth 1 -type f -exec chmod 0644 {} +
fi
if [[ "$FLAVOR" == server ]]; then
    firewall-cmd --permanent --zone=drop --add-service=ssh
    systemctl enable sshd.service
fi
systemctl disable balboa-harden.service
python3 /usr/local/libexec/balboa/package_source.py release
grep -qxF '!/var/lib/balboa' /etc/aide.conf || printf '\n!/var/lib/balboa\n' >> /etc/aide.conf
aide --init
mv /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz
python3 /usr/local/libexec/balboa/native_checks.py --dvd-only > "$out/native-initial-complete.json"
touch "$state/remediated"
if [[ "$DESKTOP" == yes ]]; then
    systemctl unmask --runtime packagekit.service
fi
if [[ "$LAB" == yes ]]; then
    printf '\nBALBOA_REMEDIATION_COMPLETE\n' > /dev/ttyS0
fi
sync
systemctl --no-block reboot
