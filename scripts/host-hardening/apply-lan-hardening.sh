#!/usr/bin/env bash
# Trial SSH + dedicated IPv4/IPv6 firewall. Never changes Docker tables.
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
source_dir=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
# Root execution sources trusted local settings; do not load unreviewed files.
source "$source_dir/local-config.sh"
rules_source="$source_dir/../../config/host-hardening/lan-hardening.nft"
ssh_file=/etc/ssh/sshd_config.d/00-local-hardening.conf
rules=/etc/pi-lan-guard.nft
service=/etc/systemd/system/pi-lan-guard.service
for path in "$ssh_file" "$rules" "$service"; do
  [[ ! -e $path ]] || { echo "Already exists: $path; review before rerunning."; exit 1; }
done
! nft list table inet pi_lan_guard >/dev/null 2>&1 || { echo 'Firewall table already exists.'; exit 1; }
[[ -s /home/${HARDENING_USER}/.ssh/authorized_keys ]]
ip -4 addr show eth0 | grep -F "${PI_IPV4_CIDR}" >/dev/null
ip -6 addr show eth0 | grep -F "${LAN_IPV6_MATCH}" >/dev/null
/usr/sbin/sshd -t
nft -c -f "$rules_source"
umask 077
backup=$(mktemp -d /root/lan-hardening-backup.XXXXXX)
cp -a /etc/ssh "$backup/ssh"
nft list ruleset > "$backup/rules-before.nft"
cat > "$backup/rollback.sh" <<'ROLLBACK'
#!/usr/bin/env bash
set -eu
systemctl disable pi-lan-guard.service 2>/dev/null || true
if nft list table inet pi_lan_guard >/dev/null 2>&1; then nft delete table inet pi_lan_guard; fi
rm -f /etc/systemd/system/pi-lan-guard.service /etc/pi-lan-guard.nft /etc/ssh/sshd_config.d/00-local-hardening.conf
systemctl daemon-reload
/usr/sbin/sshd -t
systemctl reload ssh
ROLLBACK
chmod 700 "$backup/rollback.sh"
unit="lan-hardening-rollback-$(date +%s)"
systemd-run --unit="$unit" --on-active=10m /bin/bash "$backup/rollback.sh"
on_error() {
  failed_status=$?
  trap - ERR
  printf 'ERROR: line %s exited %s; restoring original configuration.\n' "$1" "$failed_status" >&2
  /bin/bash "$backup/rollback.sh"
  systemctl stop "$unit.timer"
  printf 'Rollback completed. Backup: %s\n' "$backup" >&2
  exit "$failed_status"
}
trap 'on_error $LINENO' ERR
install -m 600 "$rules_source" "$rules"
cat > "$ssh_file" <<'CONFIG'
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
CONFIG
/usr/sbin/sshd -t
/usr/sbin/sshd -T > "$backup/sshd-effective-staged.txt"
grep -x 'passwordauthentication no' "$backup/sshd-effective-staged.txt" >/dev/null
grep -x 'permitrootlogin no' "$backup/sshd-effective-staged.txt" >/dev/null
cat > "$service" <<'SERVICE'
[Unit]
Description=Home LAN guard for host and Docker ingress
Before=network-pre.target docker.service
Wants=network-pre.target
After=local-fs.target
[Service]
Type=oneshot
ExecStart=/usr/sbin/nft -f /etc/pi-lan-guard.nft
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl start pi-lan-guard.service
systemctl reload ssh
cat > "$backup/commit.sh" <<COMMIT
#!/usr/bin/env bash
set -eu
# Refuse to commit if the timed rollback already ran.
test -f /etc/pi-lan-guard.nft
nft list table inet pi_lan_guard >/dev/null
/usr/sbin/sshd -t
systemctl is-active --quiet '$unit.timer'
systemctl enable pi-lan-guard.service
systemctl stop '$unit.timer'
echo 'Committed: key-only SSH and persistent LAN firewall.'
COMMIT
chmod 700 "$backup/commit.sh"
trap - ERR
printf 'STAGED: keep this recovery terminal open; rollback in 10 minutes.\n'
printf 'Verify fresh key logins, DNS and web access independently now.\n'
printf 'After successful independent verification: sudo bash %s/commit.sh\n' "$backup"
printf 'Rollback: sudo bash %s/rollback.sh\n' "$backup"
printf 'Do not reboot during the trial. IPv6 allowed prefix: %s.\n' "$LAN_IPV6_PREFIX"
