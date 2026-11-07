#!/bin/bash
set -euo pipefail
source /etc/balboa/image.conf
if (( $(id -u "$ADMIN_USER") < 1000 )); then
    printf 'The administrator account uses a reserved system identity.\n' >&2
    exit 1
fi
install -d -m 0700 /var/lib/balboa/evidence
install -d /etc/ssh/sshd_config.d /etc/sysctl.d /etc/security/pwquality.conf.d /etc/audit/rules.d
cat > /etc/ssh/sshd_config.d/00-balboa.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
X11Forwarding no
MaxAuthTries 3
AllowGroups wheel
LoginGraceTime 60
EOF
cat > /etc/sysctl.d/60-balboa.conf <<'EOF'
kernel.randomize_va_space = 2
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.suid_dumpable = 0
net.ipv4.ip_forward = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
EOF
cat > /etc/security/pwquality.conf.d/60-balboa.conf <<'EOF'
minlen = 15
minclass = 4
difok = 2
maxrepeat = 3
enforce_for_root
EOF
cat > /etc/security/faillock.conf <<'EOF'
deny = 5
fail_interval = 900
unlock_time = 900
even_deny_root
root_unlock_time = 900
EOF
cat > /etc/profile.d/60-balboa.sh <<'EOF'
umask 027
readonly TMOUT=900
export TMOUT
EOF
cat > /etc/sudoers.d/60-balboa <<'EOF'
Defaults use_pty
Defaults logfile="/var/log/sudo.log"
Defaults timestamp_timeout=5
EOF
chmod 0440 /etc/sudoers.d/60-balboa
visudo -cf /etc/sudoers
sed -i -E 's/^UMASK[[:space:]]+.*/UMASK 027/; s/^PASS_MAX_DAYS[[:space:]]+.*/PASS_MAX_DAYS 90/; s/^PASS_MIN_DAYS[[:space:]]+.*/PASS_MIN_DAYS 1/' /etc/login.defs
chage --maxdays 90 --mindays 1 --warndays 7 "$ADMIN_USER"
cat > /etc/issue <<'EOF'
Authorized use only. The system records activity.
EOF
cp /etc/issue /etc/issue.net
cat > /etc/ssh/sshd_config.d/01-balboa-banner.conf <<'EOF'
Banner /etc/issue.net
EOF
install -d /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/60-balboa.conf <<'EOF'
[Journal]
Storage=persistent
Compress=yes
ForwardToSyslog=yes
EOF
cat > /etc/audit/rules.d/60-balboa.rules <<'EOF'
-b 8192
-f 1
-w /etc/passwd -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/sudoers -p wa -k scope
-w /etc/sudoers.d -p wa -k scope
-w /etc/ssh/sshd_config -p wa -k sshd
-w /etc/ssh/sshd_config.d -p wa -k sshd
EOF
systemctl disable sshd.service 2>/dev/null || true
systemctl mask kdump.service
if [[ "$DESKTOP" == yes ]]; then
    install -d /etc/dconf/profile /etc/dconf/db/local.d /etc/dconf/db/local.d/locks
    cat > /etc/dconf/db/local.d/00-balboa <<'EOF'
[org/gnome/desktop/session]
idle-delay=uint32 900
[org/gnome/desktop/screensaver]
lock-enabled=true
lock-delay=uint32 0
[org/gnome/login-screen]
disable-user-list=true
EOF
    printf 'user-db:user\nsystem-db:local\n' > /etc/dconf/profile/user
    printf 'user-db:user\nsystem-db:local\n' > /etc/dconf/profile/gdm
    printf '/org/gnome/desktop/session/idle-delay\n/org/gnome/desktop/screensaver/lock-enabled\n/org/gnome/desktop/screensaver/lock-delay\n' > /etc/dconf/db/local.d/locks/00-balboa
    dconf update
fi
if [[ "$FLAVOR" == laptop ]]; then
    systemctl enable bluetooth.service tuned.service tuned-ppd.service
fi
# Network access requires operator firewall rules after installation.
firewall-offline-cmd --set-default-zone=drop
restorecon -RF /etc/balboa /usr/local/libexec/balboa /etc/systemd/system
