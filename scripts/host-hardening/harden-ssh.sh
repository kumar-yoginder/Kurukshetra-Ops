#!/usr/bin/env bash
# Stage key-only SSH with rollback. Commit only after independent login testing.
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
source_dir=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
# Root execution sources trusted local settings; do not load unreviewed files.
source "$source_dir/local-config.sh"
target=/etc/ssh/sshd_config.d/00-local-hardening.conf
[[ ! -e $target ]] || { echo 'Existing hardening file: review before rerunning.'; exit 1; }
/usr/sbin/sshd -t
[[ -s /home/${HARDENING_USER}/.ssh/authorized_keys ]] || exit 1
umask 077
backup=$(mktemp -d /root/ssh-hardening-backup.XXXXXX)
cp -a /etc/ssh "$backup/ssh"
cat > "$backup/rollback.sh" <<'ROLLBACK'
#!/usr/bin/env bash
set -eu
rm -f /etc/ssh/sshd_config.d/00-local-hardening.conf
/usr/sbin/sshd -t
systemctl reload ssh
ROLLBACK
chmod 700 "$backup/rollback.sh"
unit="ssh-hardening-rollback-$(date +%s)"
systemd-run --unit="$unit" --on-active=10m /bin/bash "$backup/rollback.sh"
on_error() { trap - ERR; /bin/bash "$backup/rollback.sh"; systemctl stop "$unit.timer"; exit 1; }
trap on_error ERR
cat > "$target" <<'CONFIG'
# Managed by reviewed harden-ssh.sh; forwarding retained for existing tools.
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
CONFIG
/usr/sbin/sshd -t
/usr/sbin/sshd -T | grep -qx 'passwordauthentication no'
/usr/sbin/sshd -T | grep -qx 'permitrootlogin no'
systemctl reload ssh
trap - ERR
printf 'STAGED: keep this recovery terminal open. Automatic rollback in 10 minutes.\n'
printf 'Verify independent Ethernet/Wi-Fi key logins and DNS now.\n'
printf 'Only after successful verification, commit with: sudo systemctl stop %s.timer\n' "$unit"
printf 'Manual rollback: sudo bash %s/rollback.sh\n' "$backup"
printf 'Do not reboot during the trial; the rollback timer is transient.\n'
