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
chage --lastday -1 balboasmoke
install -d /etc/balboa /usr/local/libexec/balboa
cp /workspace/guest/*.sh /usr/local/libexec/balboa/
printf 'FLAVOR=%s\nADMIN_USER=balboasmoke\nDESKTOP=%s\nLAB=no\n' "$flavor" "$desktop" > /etc/balboa/image.conf
python3 - "$flavor" <<'PY'
import json
from pathlib import Path
import sys
definition = json.loads(Path('/workspace/flavors', sys.argv[1] + '.json').read_text())
Path('/etc/balboa/native-policy.json').write_text(json.dumps({'excluded_packages': definition['exclude']}))
PY
if [[ "$desktop" == yes ]]; then
    install -d -m 0755 /usr/share/backgrounds/balboa
    install -m 0644 "$(dirname "$ks")/branding/wallpaper.png" "$(dirname "$ks")/branding/login.png" /usr/share/backgrounds/balboa/
fi
bash /workspace/guest/baseline.sh
test -f /etc/audit/rules.d/60-balboa.rules
visudo -cf /etc/sudoers
runuser -u balboasmoke -- test -r /etc/profile.d/60-balboa.sh
last_change=$(getent shadow balboasmoke | cut -d: -f3)
[[ "$last_change" =~ ^[0-9]+$ ]]
if [[ "$desktop" == yes ]]; then
    runuser -u balboasmoke -- test -r /etc/dconf/profile/user
    runuser -u balboasmoke -- test -r /etc/dconf/db/local
    runuser -u gdm -- test -r /usr/share/backgrounds/balboa/login.png
    [[ "$(runuser -u balboasmoke -- gsettings get org.gnome.desktop.background picture-uri)" == "'file:///usr/share/backgrounds/balboa/wallpaper.png'" ]]
    [[ "$(runuser -u gdm -- env DCONF_PROFILE=gdm gsettings get org.gnome.login-screen logo)" == "'/usr/share/backgrounds/balboa/login.png'" ]]
fi
printf 'The minimal post-installation script passed for %s.\n' "$flavor"
