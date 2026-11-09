#!/bin/bash
set -euo pipefail
source /etc/balboa/image.conf
if [[ "${BOOT_SPLASH:-no}" != yes ]]; then
    exit 0
fi

theme=/usr/share/plymouth/themes/balboa
test -s "$theme/balboa.script"
test -s "$theme/spinner.png"
test -s "$theme/entry.png"
install -m 0644 /boot/grub2/themes/balboa/boot.png "$theme/boot.png"
install -d -m 0755 /etc/plymouth /etc/dracut.conf.d
cat > /etc/plymouth/plymouthd.conf <<'CONF'
[Daemon]
Theme=balboa
ShowDelay=0
DeviceTimeout=8
CONF
cat > /etc/dracut.conf.d/60-balboa-plymouth.conf <<'CONF'
add_dracutmodules+=" plymouth "
install_items+=" /usr/bin/fc-match /etc/fonts/fonts.conf /etc/fonts/conf.d/55-balboa-inter.conf /usr/share/fonts/balboa/Inter-Regular.ttf "
CONF
chmod 0644 /etc/plymouth/plymouthd.conf /etc/dracut.conf.d/60-balboa-plymouth.conf
plymouth-set-default-theme balboa
restorecon -RF "$theme" /etc/plymouth /etc/dracut.conf.d
if systemd-detect-virt --container --quiet; then
    exit 0
fi
dracut --regenerate-all --force
