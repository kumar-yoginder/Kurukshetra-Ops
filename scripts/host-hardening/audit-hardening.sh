#!/usr/bin/env bash
# Read-only privileged audit. No passwords, private keys, container environments,
# application configuration contents, or authentication logs are collected.
set -uo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
source_dir=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
# Root execution sources trusted local settings; do not load unreviewed files.
source "$source_dir/local-config.sh"
section() { printf '\n## %s\n' "$1"; }
section 'Time and SSH effective configuration'
date -Is
/usr/sbin/sshd -t
/usr/sbin/sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|authenticationmethods|permitemptypasswords|maxauthtries|allowusers|allowgroups|denyusers|denygroups|usepam|allowtcpforwarding|x11forwarding|logingracetime) '
section 'SSH Match and include directives'
grep -R -E '^[[:space:]]*(Match|Include|AllowUsers|AllowGroups|DenyUsers|DenyGroups)' /etc/ssh/sshd_config /etc/ssh/sshd_config.d 2>/dev/null || true
section 'Account lock state and sudo policy validation'
passwd -S root
passwd -S "$HARDENING_USER"
visudo -c
sudo -l -U "$HARDENING_USER"
section 'Firewall'
ufw status verbose
iptables --version
ip6tables --version
iptables-save
ip6tables-save
if command -v nft >/dev/null; then nft list ruleset; fi
section 'Listeners and IPv6 routes'
ss -lntup
ip -6 route
section 'Automatic updates'
apt-config dump | grep -E 'APT::Periodic|Unattended-Upgrade::(Allowed-Origins|Origins-Pattern|Automatic-Reboot|Package-Blacklist)' || true
systemctl is-enabled apt-daily.timer apt-daily-upgrade.timer unattended-upgrades
stat -c '%y %n' /var/lib/apt/periodic/update-success-stamp /var/lib/apt/periodic/upgrade-stamp 2>/dev/null || true
if test -f /var/run/reboot-required.pkgs; then cat /var/run/reboot-required.pkgs; fi
section 'Security confinement'
aa-status
section 'Backup service names and known network backups'
systemctl list-timers --all --no-pager | grep -Ei 'backup|borg|restic|duplicity|apt' || true
find /root -maxdepth 1 -type d -name 'eth0-static-backup.*' -printf '%f\n'
section 'Audit finished'
