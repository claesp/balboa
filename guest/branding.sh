#!/bin/bash
set -euo pipefail
source /etc/balboa/image.conf

if [[ "$DESKTOP" == yes ]]; then
    test -s /usr/share/backgrounds/balboa/wallpaper.png
    test -s /usr/share/backgrounds/balboa/login.png
    install -d -m 0755 /etc/dconf/profile /etc/dconf/db/local.d /etc/dconf/db/gdm.d
    cat > /etc/dconf/db/local.d/01-balboa-background <<'EOF'
[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/balboa/wallpaper.png'
picture-uri-dark='file:///usr/share/backgrounds/balboa/wallpaper.png'
picture-options='zoom'
EOF
    cat > /etc/dconf/db/gdm.d/01-balboa-logo <<'EOF'
[org/gnome/login-screen]
logo='/usr/share/backgrounds/balboa/login.png'
EOF
    cat > /etc/dconf/profile/gdm <<'EOF'
user-db:user
system-db:gdm
system-db:local
file-db:/usr/share/gdm/greeter-dconf-defaults
EOF
    dconf update
    chmod 0644 /etc/dconf/profile/gdm /etc/dconf/db/local.d/01-balboa-background \
        /etc/dconf/db/gdm.d/01-balboa-logo /etc/dconf/db/local /etc/dconf/db/gdm
    restorecon -RF /usr/share/backgrounds/balboa /etc/dconf
fi

if systemd-detect-virt --container --quiet; then
    exit 0
fi
test -s /boot/grub2/themes/balboa/boot.png
test -f /etc/default/grub
python3 - <<'PY'
from pathlib import Path
import re
path = Path('/etc/default/grub')
content = re.sub(r'^GRUB_TERMINAL=.*\n?', '', path.read_text(), flags=re.MULTILINE)
values = {'GRUB_THEME': '/boot/grub2/themes/balboa/theme.txt', 'GRUB_GFXMODE': 'auto',
          'GRUB_TERMINAL_OUTPUT': 'gfxterm', 'GRUB_TIMEOUT_STYLE': 'menu', 'GRUB_TIMEOUT': '5'}
for key, value in values.items():
    content = re.sub(r'^' + key + r'=.*\n?', '', content, flags=re.MULTILINE)
    content += f'\n{key}="{value}"\n'
path.write_text(content)
PY
restorecon -RF /boot/grub2/themes/balboa
grub2-editenv - unset menu_auto_hide
grub2-mkconfig -o /boot/grub2/grub.cfg
