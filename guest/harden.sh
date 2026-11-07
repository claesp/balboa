#!/bin/bash
set -euo pipefail
umask 077
source /etc/balboa/image.conf
state=/var/lib/balboa
out=$state/evidence
install -d -m 0700 "$out"
exec >> "$out/harden.log" 2>&1
ds=/usr/share/xml/scap/ssg/content/ssg-rl10-ds.xml
test -f "$ds"
oscap info --profiles "$ds" | grep -F "${PROFILE}:"
rpm -qa | sort > "$out/packages.txt"
sha256sum "$ds" > "$out/datastream.sha256"
cp /etc/balboa/image.conf "$out/image.conf"
oscap info "$ds" > "$out/content.txt"
set +e
oscap xccdf eval --remediate --profile "$PROFILE" \
    --results "$out/remediation.xml" --results-arf "$out/remediation-arf.xml" \
    --report "$out/remediation.html" "$ds"
rc=$?
set -e
[[ "$rc" == 0 || "$rc" == 2 ]]
python3 /usr/local/libexec/balboa/result_gate.py "$out/remediation.xml" \
    --profile "$PROFILE" --allow-findings > "$out/remediation-summary.json"
aide --init
mv /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz
touch "$state/remediated"
sync
systemctl --no-block reboot
