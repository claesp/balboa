#!/bin/bash
# This file is sourced by the first-boot services.
balboa_failure() {
    local status=$?
    trap - ERR
    if [[ ! -e /var/lib/balboa/remediated ]]; then
        python3 /usr/local/libexec/balboa/package_source.py guard || true
    fi
    printf '%s\n' "$status" > /var/lib/balboa/evidence/service-exit-status
    journalctl -b -u systemd-journal-upload.service --no-pager > /var/lib/balboa/evidence/journal-upload.log || true
    if [[ "$LAB" == yes ]]; then
        bash /usr/local/libexec/balboa/export.sh || true
        sync
        systemctl --no-block poweroff || true
    fi
    exit "$status"
}
trap balboa_failure ERR
