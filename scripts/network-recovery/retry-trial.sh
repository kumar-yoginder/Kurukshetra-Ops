#!/bin/sh
# Clean retry for the first failed trial; review before running locally with sudo.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run locally with sudo.' >&2; exit 1; }
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project=$(CDPATH= cd -- "$base/../.." && pwd)
# Stop the old timer first so it cannot undo a replacement trial.
for unit in kurukshetra-network-recovery-rollback.timer kurukshetra-network-recovery-rollback.service kurukshetra-network-recovery.service; do
 if systemctl show "$unit" -p LoadState --value 2>/dev/null | grep -qv '^not-found$'; then
  systemctl stop "$unit"
 fi
done
systemctl reset-failed kurukshetra-network-recovery.service kurukshetra-network-recovery-rollback.service 2>/dev/null || true
exec sh "$base/install-trial.sh" "$project/config/network-recovery/recovery.json"
