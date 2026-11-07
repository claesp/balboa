#!/bin/bash
set -euo pipefail
ks=$1
flavor=$2
case "$flavor" in
    server) desktop=no ;;
    workstation|laptop) desktop=yes ;;
    *) exit 1 ;;
esac
mapfile -t packages < <(python3 - "$ks" <<'PY'
from pykickstart.parser import KickstartParser
from pykickstart.version import makeVersion
import sys
parser = KickstartParser(makeVersion("RHEL10"))
parser.readKickstart(sys.argv[1])
print("\n".join(parser.handler.packages.packageList))
PY
)
dnf -y --setopt=install_weak_deps=False install "${packages[@]}" > /tmp/balboa-packages.log 2>&1 || {
    tail -40 /tmp/balboa-packages.log
    exit 1
}
useradd --uid 1000 balboasmoke
install -d /etc/balboa /usr/local/libexec/balboa
cp /workspace/guest/*.sh /usr/local/libexec/balboa/
printf 'FLAVOR=%s\nADMIN_USER=balboasmoke\nDESKTOP=%s\nLAB=no\n' "$flavor" "$desktop" > /etc/balboa/image.conf
bash /workspace/guest/baseline.sh
test -f /etc/audit/rules.d/60-balboa.rules
visudo -cf /etc/sudoers
printf 'The minimal post-installation script passed for %s.\n' "$flavor"
