#!/bin/sh
# Managed by Kurukshetra-Ops network-recovery v1
# MANUAL root operation: installs and enables monitor at boot. No network simulation.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$base/persistent-common.sh"
require_root
[ "$#" -le 1 ] || { echo 'Usage: install-persistent.sh [/absolute/private-config.json]' >&2; exit 1; }
config=${1:-/etc/kurukshetra-network-recovery.json}
case "$config" in /*) ;; *) echo 'Use an absolute config path.' >&2; exit 1;; esac
check_unit_ownership
python3 "$base/ethernet_wifi_recovery.py" --config "$config" --status
systemd-analyze verify "$base/kurukshetra-network-recovery.service"
stop_owned_trial_timer
# Stop old monitor before replacing executable/config. Shutdown keeps Wi-Fi available.
systemctl stop "$unit" 2>/dev/null || true
install -o root -g root -m 0755 "$base/ethernet_wifi_recovery.py" /usr/local/sbin/kurukshetra-network-recovery
install -o root -g root -m 0755 "$base/rollback.sh" /usr/local/sbin/kurukshetra-network-recovery-rollback
if [ "$config" != /etc/kurukshetra-network-recovery.json ]; then
    install -o root -g root -m 0600 "$config" /etc/kurukshetra-network-recovery.json
fi
chown root:root /etc/kurukshetra-network-recovery.json
chmod 0600 /etc/kurukshetra-network-recovery.json
install -o root -g root -m 0644 "$base/kurukshetra-network-recovery.service" "$unit_file"
systemctl daemon-reload
systemctl reset-failed "$unit" 2>/dev/null || true
systemctl enable --now "$unit"
systemctl --no-pager status "$unit"
printf '%s\n' 'Persistent monitoring enabled. No cable or outage test was performed.' 'Disable safely using scripts/network-recovery/disable-persistent.sh.'
