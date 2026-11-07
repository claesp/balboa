#!/bin/bash
set -euo pipefail
umask 077
source /etc/balboa/image.conf
state=/var/lib/balboa
out=$state/evidence
exec >> "$out/audit.log" 2>&1
ds=/usr/share/xml/scap/ssg/content/ssg-rl10-ds.xml
set +e
oscap xccdf eval --profile "$PROFILE" --results "$out/assessment.xml" \
    --results-arf "$out/assessment-arf.xml" --report "$out/assessment.html" "$ds"
scan=$?
python3 /usr/local/libexec/balboa/result_gate.py "$out/assessment.xml" \
    --profile "$PROFILE" > "$out/summary.json"
gate=$?
set -e
printf '%s\n' "$scan" > "$out/oscap-exit-status"
lsblk -o NAME,TYPE,FSTYPE,MOUNTPOINTS > "$out/storage.txt"
findmnt > "$out/mounts.txt"
getenforce > "$out/selinux.txt"
systemctl --failed --no-pager > "$out/failed-units.txt"
if [[ "$scan" == 0 && "$gate" == 0 ]]; then
    touch "$state/assessment-passed"
else
    rm -f "$state/assessment-passed"
fi
touch "$state/assessed"
if [[ "$LAB" == yes ]]; then
    # Export through a dedicated guest channel. No host directory is shared.
    tar -C "$state" -czf /dev/virtio-ports/org.balboa.evidence evidence
    sync
    systemctl --no-block poweroff
fi
[[ "$scan" == 0 && "$gate" == 0 ]]
