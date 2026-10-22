#!/usr/bin/env bash
# Temporary Ubuntu trial only. Run after reviewing a trusted local config directory.
set -Eeuo pipefail
[[ $EUID == 0 && $# == 1 ]] || { echo 'Usage: sudo bash trial.sh TRUSTED_CONFIG_DIRECTORY'; exit 1; }
exec 9>/run/kurukshetra-tor.lock
flock -x 9
source "$1/local.env"
: "${CLIENT_TUNNEL_IP:?}" "${ENDPOINT_IP:?}" "${MGMT_IP:?}" "${MGMT_IF:?}" "${LAN_IF:?}" "${LAN_GATEWAY:?}"
[[ $ENDPOINT_IP =~ ^[0-9.]+$ && $MGMT_IP =~ ^[0-9.]+$ && $LAN_GATEWAY =~ ^[0-9.]+$ ]]
[[ $MGMT_IF =~ ^[a-zA-Z0-9]+$ && $LAN_IF =~ ^[a-zA-Z0-9]+$ ]]
# Current server subnet is fixed; reserve .1 for the gateway and .255 broadcast.
[[ $CLIENT_TUNNEL_IP =~ ^10\.77\.0\.([0-9]{1,3})$ ]] || { echo 'CLIENT_TUNNEL_IP must be in 10.77.0.2–254'; exit 1; }
last_octet=${BASH_REMATCH[1]}
[[ $last_octet != 0* ]] && (( 10#$last_octet >= 2 && 10#$last_octet <= 254 )) || { echo 'Invalid client tunnel address'; exit 1; }
[[ -s $1/wg.conf ]]
[[ ! -e /run/kurukshetra-tor-session ]] || { echo 'Managed session already exists; disconnect first.'; exit 1; }
! ip link show torwg0 >/dev/null 2>&1
! nft list table inet tor_client >/dev/null 2>&1
! ip rule show | grep -qE '^(9996|9997|9998|9999|10000):'
[[ -z $(ip route show table 51877 2>/dev/null) ]]
umask 077
backup=$(mktemp -d /root/tor-client-trial.XXXXXX)
ip -j address > "$backup/addresses.json"
ip -j route show table all > "$backup/routes.json"
ip rule show > "$backup/rules.txt"
nft list ruleset > "$backup/firewall.nft"
cat > "$backup/rollback.sh" <<'ROLLBACK'
#!/bin/bash
set -eu
# An internal error cleanup inherits the already locked descriptor; timer/manual
# rollback opens the same lock independently. Never reacquire via a new fd in a child.
if [[ ${1:-} == --lock-inherited ]]; then
 [[ $(readlink /proc/self/fd/9) == /run/kurukshetra-tor.lock ]] || exit 1
else
 exec 9>/run/kurukshetra-tor.lock
fi
flock -x 9
own_backup=$(cd -- "$(dirname -- "$0")" && pwd)
[[ -f /run/kurukshetra-tor-session ]] || exit 0
IFS= read -r current_backup < /run/kurukshetra-tor-session
[[ $current_backup == "$own_backup" ]] || exit 0
if [[ ${1:-} == --timer && $(sed -n '3p' /run/kurukshetra-tor-session) == confirmed ]]; then exit 0; fi
# Stop only this generation's timer, never another session.
current_unit=$(sed -n '2p' /run/kurukshetra-tor-session)
if [[ $current_unit =~ ^tor-client-trial-[0-9]+$ ]]; then
 systemctl stop "$current_unit.timer" 2>/dev/null || true
fi
resolvectl revert torwg0 2>/dev/null || true
for priority in 9996 9997 9998 9999 10000; do ip rule delete priority "$priority" 2>/dev/null || true; done
ip route flush table 51877 2>/dev/null || true
ip link delete torwg0 2>/dev/null || true
if nft list table inet tor_client >/dev/null 2>&1; then nft delete table inet tor_client; fi
rm -f /run/kurukshetra-tor-session
printf 'Trial reverted to the original network path.\n'
ROLLBACK
chmod 700 "$backup/rollback.sh"
unit="tor-client-trial-$(date +%s)"
printf '%s\n%s\n' "$backup" "$unit" > /run/kurukshetra-tor-session
trap 'trap - ERR; bash "$backup/rollback.sh" --lock-inherited; systemctl stop "$unit.timer" 2>/dev/null || true; exit 1' ERR
systemd-run --unit="$unit" --on-active=15m /bin/bash "$backup/rollback.sh" --timer
cat > "$backup/client.nft" <<RULES
table inet tor_client {
 chain output {
  type filter hook output priority -10; policy drop;
  oifname "lo" accept
  # Host-only SSH recovery; only replies to the Mac's management address.
  oifname "$MGMT_IF" ip daddr $MGMT_IP tcp sport 22 ct state established accept
  # Authenticated tunnel transport to this endpoint only.
  oifname "$LAN_IF" ip daddr $ENDPOINT_IP udp dport 51820 accept
  # DHCP lease maintenance only; no general LAN/DNS exceptions.
  oifname { "$LAN_IF", "$MGMT_IF" } udp sport 68 udp dport 67 accept
  oifname "torwg0" meta nfproto ipv4 meta l4proto tcp accept
  oifname "torwg0" meta nfproto ipv4 udp dport 53 accept
  counter drop
 }
 chain forward {
  type filter hook forward priority -10; policy drop;
 }
}
RULES
nft -c -f "$backup/client.nft"
nft -f "$backup/client.nft"
ip link add torwg0 type wireguard
wg setconf torwg0 "$1/wg.conf"
wg set torwg0 fwmark 51877
ip address add "$CLIENT_TUNNEL_IP/32" dev torwg0
ip link set torwg0 mtu 1380 up
ip route add default dev torwg0 table 51877
ip rule add priority 9996 to "$MGMT_IP/32" lookup main
ip rule add priority 9997 to "$ENDPOINT_IP/32" lookup main
ip rule add priority 9998 to "$LAN_GATEWAY/32" lookup main
ip rule add priority 9999 to 255.255.255.255/32 lookup main
ip rule add priority 10000 not fwmark 51877 lookup 51877
resolvectl dns torwg0 10.77.0.1
resolvectl domain torwg0 '~.'
resolvectl default-route torwg0 yes
resolvectl dnsovertls torwg0 no
resolvectl dnssec torwg0 no
printf '%s\n%s\n' "$backup" "$unit" > /run/kurukshetra-tor-session
trap - ERR
printf 'TRIAL_STARTED\nBackup: %s\nRollback timer: %s.timer\n' "$backup" "$unit"
printf 'Temporary trial only; automatic baseline restore in 15 minutes. Do not reboot.\n'
