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
install -m 0755 /workspace/guest/package_source.py /usr/local/libexec/balboa/
splash=$(python3 - "$ks" <<'PYTHON'
import json, pathlib, sys
print("yes" if json.loads(pathlib.Path(sys.argv[1]).with_suffix(".json").read_text())["boot_splash"] else "no")
PYTHON
)
if [[ "$desktop" == yes || "$splash" == yes ]]; then
    install -d -m 0755 /usr/share/fonts/balboa
    install -m 0644 /workspace/assets/fonts/Inter-Regular.ttf /usr/share/fonts/balboa/
    install -d /etc/fonts/conf.d
    install -m 0644 /workspace/guest/Inter.conf /etc/fonts/conf.d/55-balboa-inter.conf
fi
printf 'FLAVOR=%s\nADMIN_USER=balboasmoke\nDESKTOP=%s\nLAB=no\n' "$flavor" "$desktop" > /etc/balboa/image.conf
python3 - "$flavor" <<'PY'
import json
from pathlib import Path
import sys
definition = json.loads(Path('/workspace/flavors', sys.argv[1] + '.json').read_text())
Path('/etc/balboa/native-policy.json').write_text(json.dumps({'excluded_packages': definition['exclude']}))
PY
if [[ "$desktop" == yes ]]; then
    install -d -m 0755 /etc/firefox/policies
    python3 - "$ks" <<'PYTHON'
import base64
import json
from pathlib import Path
import shlex
import sys
destination = '/etc/firefox/policies/policies.json'
lines = [line for line in Path(sys.argv[1]).read_text().splitlines() if line.endswith(' > ' + destination)]
if len(lines) != 1:
    raise ValueError('The desktop Kickstart requires one Firefox policy file.')
command = shlex.split(lines[0])
if command[:2] != ['printf', '%s'] or command[3:] != ['|', 'base64', '-d', '>', destination]:
    raise ValueError('The Firefox policy uses an unexpected file format.')
policy = base64.b64decode(command[2], validate=True)
json.loads(policy)
Path(destination).write_bytes(policy)
Path(destination).chmod(0o644)
PYTHON
    install -d -m 0755 /usr/share/backgrounds/balboa
    install -m 0644 "$(dirname "$ks")/branding/wallpaper.png" "$(dirname "$ks")/branding/login.png" /usr/share/backgrounds/balboa/
fi
install -d -m 0755 /boot/grub2/themes/balboa
install -m 0644 "$(dirname "$ks")/branding/boot.png" /boot/grub2/themes/balboa/boot.png
printf 'BOOT_SPLASH=%s\n' "$splash" >> /etc/balboa/image.conf
if [[ "$splash" == yes ]]; then
    install -d -m 0755 /usr/share/plymouth/themes/balboa
    install -m 0644 /workspace/guest/plymouth/* /usr/share/plymouth/themes/balboa/
    install -m 0644 "$(dirname "$ks")/branding/plymouth/"*.png /usr/share/plymouth/themes/balboa/
fi
bash /workspace/guest/baseline.sh
if [[ "$splash" == yes ]]; then
    [[ "$(plymouth-set-default-theme)" == balboa ]]
    [[ "$(fc-match -f '%{family}' sans-serif)" == Inter ]]
    cmp /boot/grub2/themes/balboa/boot.png /usr/share/plymouth/themes/balboa/boot.png
    test -s /etc/dracut.conf.d/60-balboa-plymouth.conf
fi
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
    runuser -u balboasmoke -- test -r /etc/firefox/policies/policies.json
    rpm -ql gnome-software | grep '/libgs_plugin_packagekit.so$' > /dev/null
    runuser -u balboasmoke -- python3 /workspace/tests/firefox_checks.py
fi
printf 'The minimal post-installation script passed for %s.\n' "$flavor"
