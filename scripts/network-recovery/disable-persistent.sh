#!/bin/sh
# Managed by Kurukshetra-Ops network-recovery v1
# MANUAL root operation. --uninstall removes only owned service unit, keeping recovery files/config.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$base/persistent-common.sh"
require_root
[ "$#" = 0 ] || { [ "$#" = 1 ] && [ "$1" = --uninstall ]; } || { echo 'Usage: disable-persistent.sh [--uninstall]' >&2; exit 1; }
check_unit_ownership
stop_owned_trial_timer
systemctl disable "$unit" 2>/dev/null || true
systemctl stop "$unit" 2>/dev/null || true
# Independent restore covers an already failed/killed monitor; does not stop itself.
/usr/local/sbin/kurukshetra-network-recovery --restore
if [ "${1:-}" = --uninstall ] && [ -f "$unit_file" ]; then
    rm -- "$unit_file"
    systemctl daemon-reload
    systemctl reset-failed "$unit" 2>/dev/null || true
fi
printf '%s\n' 'Monitoring disabled; Wi-Fi requested up and local reply policy retained.' 'Private config and recovery binaries remain installed. No netplan or Wi-Fi credentials changed.' 'The reserved recovery policy is intentionally kept until reboot to preserve emergency SSH.'
