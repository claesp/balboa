#!/bin/bash
# This file is sourced by the first-boot services.
balboa_failure() {
    local status=$?
    trap - ERR
    printf '%s\n' "$status" > /var/lib/balboa/evidence/service-exit-status
    if [[ "$LAB" == yes ]]; then
        tar -C /var/lib/balboa -czf /dev/virtio-ports/org.balboa.evidence evidence || true
        sync
        systemctl --no-block poweroff || true
    fi
    exit "$status"
}
trap balboa_failure ERR
