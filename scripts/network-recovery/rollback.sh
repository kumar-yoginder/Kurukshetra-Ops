#!/bin/sh
# Independent rollback, also works when the monitor crashed or was killed.
set -u
[ "$(id -u)" = 0 ] || exit 1
systemctl stop kurukshetra-network-recovery.service || true
exec /usr/local/sbin/kurukshetra-network-recovery --restore
