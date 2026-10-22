#!/bin/sh
# Install as root-owned before authorizing this fixed read-only diagnostic.
set -eu
[ "$#" -eq 0 ] || exit 2
[ "$(/usr/bin/id -u)" -eq 0 ] || { echo 'Root required' >&2; exit 1; }
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
printf '\nFirewall rules (read only)\n'
/usr/sbin/nft list ruleset
printf '\nForwarding state (read only)\n'
/usr/sbin/sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding
printf '\nSSH syntax validation (read only)\n'
/usr/sbin/sshd -t
printf '\nHost services (read only)\n'
/usr/bin/systemctl is-active ssh systemd-timesyncd docker || true
printf '\nChecks finished; no settings changed\n'
