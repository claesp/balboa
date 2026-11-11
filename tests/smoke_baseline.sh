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
render_dir=$(dirname "$ks")
python3 "$render_dir/install_files.py" "$render_dir/balboa-files" /
sed -i 's/^ADMIN_USER=.*/ADMIN_USER=balboasmoke/; s/^LAB=.*/LAB=no/' /etc/balboa/image.conf
source /etc/balboa/image.conf
splash=$BOOT_SPLASH
bash /usr/local/libexec/balboa/baseline.sh
prefix=pc
if [[ "$flavor" == server ]]; then
    prefix=srv
fi
grep -Eq "^${prefix}-[a-z0-9]([a-z0-9-]*[a-z0-9])?$" /etc/hostname
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
    [[ "$(runuser -u balboasmoke -- gsettings get org.gnome.desktop.notifications show-in-lock-screen)" == false ]]
    [[ "$(runuser -u balboasmoke -- gsettings get org.gnome.desktop.search-providers disable-external)" == true ]]
    [[ "$(runuser -u balboasmoke -- gsettings get org.gnome.desktop.privacy remove-old-temp-files)" == true ]]
    grep -Fxq 'enable=none' /etc/goa.conf
    rpm -q --quiet nautilus tracker-miners
    [[ "$(systemctl --global is-enabled tracker-miner-fs-3.service)" == masked ]]
    runuser -u balboasmoke -- test -r /etc/firefox/policies/policies.json
    systemctl is-enabled --quiet dnf-automatic.timer
    dnf config-manager --help >/dev/null
    for package in gnome-software PackageKit flatpak; do
        if rpm -q --quiet "$package"; then
            printf 'The desktop contains excluded package %s.\n' "$package" >&2
            exit 1
        fi
    done
    runuser -u balboasmoke -- python3 /workspace/tests/firefox_checks.py
fi
printf 'The minimal post-installation script passed for %s.\n' "$flavor"
