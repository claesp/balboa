#!/bin/sh
set -eu
vendor=/usr/lib/systemd/system/systemd-journal-upload.service
[ "$#" -ge 1 ] && [ -f "$vendor" ] || exit 0
mkdir -p "$1"
awk '
/^\[/ { section = $0 }
section == "[Unit]" && /^[[:space:]]*(Wants|After)[[:space:]]*=/ {
    key = $0
    sub(/=.*/, "", key)
    gsub(/[[:space:]]/, "", key)
    value = $0
    sub(/^[^=]*=/, "", value)
    count = split(value, dependencies, /[[:space:]]+/)
    printf "%s=", key
    network = 0
    for (i = 1; i <= count; i++) {
        if (dependencies[i] == "" || dependencies[i] == "network-online.target") continue
        printf "%s ", dependencies[i]
        if (dependencies[i] == "network.target") network = 1
    }
    if (key == "After" && !network) printf "network.target"
    printf "\n"
    next
}
{ print }
' "$vendor" > "$1/systemd-journal-upload.service"
chmod 0644 "$1/systemd-journal-upload.service"
