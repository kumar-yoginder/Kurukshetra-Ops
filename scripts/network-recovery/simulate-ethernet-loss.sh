#!/bin/sh
# User-run controlled test: disable Ethernet only after independent restore timers exist.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run locally with sudo after review.' >&2; exit 1; }
eth=$(python3 -c 'import json; print(json.load(open("/etc/kurukshetra-network-recovery.json"))["ethernet"])')
wifi=$(python3 -c 'import json; print(json.load(open("/etc/kurukshetra-network-recovery.json"))["wifi"])')
case "$eth:$wifi" in *[!a-zA-Z0-9_:.-]*) echo 'Invalid interface settings'; exit 1;; esac
systemctl is-active --quiet kurukshetra-network-recovery.service || { echo 'Recovery monitor is not active. Start a fresh trial first.'; exit 1; }
[ "$(cat "/sys/class/net/$eth/carrier")" = 1 ] || { echo 'Ethernet is not currently linked.'; exit 1; }
# Require Wi-Fi already disconnected, otherwise this would not test activation.
python3 -c 'import sys; from pathlib import Path; flags=int(Path("/sys/class/net",sys.argv[1],"flags").read_text().strip(),16); sys.exit(1 if flags&1 else 0)' "$wifi" || { echo 'Wi-Fi is still up; wait for healthy-Ethernet delay and retry.'; exit 1; }
# Independent timers continue running even when this SSH session disconnects.
stamp=$(date +%s)
restore="kurukshetra-ethernet-test-restore-$stamp"
rollback="kurukshetra-network-test-rollback-$stamp"
systemd-run --unit="$restore" --on-active=60s --timer-property=AccuracySec=1s /usr/bin/networkctl up "$eth"
systemctl is-active --quiet "$restore.timer"
systemd-run --unit="$rollback" --on-active=3m --timer-property=AccuracySec=1s /usr/local/sbin/kurukshetra-network-recovery-rollback
systemctl is-active --quiet "$rollback.timer"
# Replacement three-minute timer is armed before stopping the original timer.
systemctl stop kurukshetra-network-recovery-rollback.timer
systemctl is-active --quiet kurukshetra-network-recovery.service
printf 'Ethernet restore armed: %s.timer (60 seconds from arming).\n' "$restore"
printf 'Monitor rollback armed: %s.timer (3 minutes from arming).\n' "$rollback"
printf 'Disabling %s now. This SSH connection is expected to drop.\n' "$eth"
networkctl down "$eth"
