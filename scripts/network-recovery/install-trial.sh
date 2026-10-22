#!/bin/sh
# Run manually as root after reviewing the files. Does not enable at boot.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run locally with sudo after review.' >&2; exit 1; }
[ "$#" = 1 ] || { echo 'Usage: install-trial.sh /absolute/path/to/private-config.json' >&2; exit 1; }
case "$1" in /*) ;; *) echo 'Use an absolute config path.' >&2; exit 1;; esac
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# Validate before installing or making any interface changes.
python3 "$base/ethernet_wifi_recovery.py" --config "$1" --status
systemctl is-active --quiet kurukshetra-network-recovery.service && { echo 'Existing trial active; stop and review it first.' >&2; exit 1; }
install -o root -g root -m 0755 "$base/ethernet_wifi_recovery.py" /usr/local/sbin/kurukshetra-network-recovery
install -o root -g root -m 0600 "$1" /etc/kurukshetra-network-recovery.json
install -o root -g root -m 0755 "$base/rollback.sh" /usr/local/sbin/kurukshetra-network-recovery-rollback
# Independent stop timer is installed FIRST. Daemon shutdown brings Wi-Fi up.
# No persistent unit is created and no existing network manager is restarted.
systemd-run --unit=kurukshetra-network-recovery-rollback --on-active=3m --timer-property=AccuracySec=1s /usr/local/sbin/kurukshetra-network-recovery-rollback
systemd-run --unit=kurukshetra-network-recovery --property=TimeoutStopSec=120 /usr/local/sbin/kurukshetra-network-recovery --monitor
printf '%s\n' 'Trial started for 3 minutes. Inspect journalctl -u kurukshetra-network-recovery.' 'Early rollback: sudo /usr/local/sbin/kurukshetra-network-recovery-rollback' 'Shutdown restores Wi-Fi; its local reply policy remains until reboot for recovery safety.'
