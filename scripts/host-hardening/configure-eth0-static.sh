#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
source_dir=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
# Root execution sources trusted local settings; do not load unreviewed files.
source "$source_dir/local-config.sh"
target=/etc/netplan/99-eth0-static.yaml
[[ ! -e $target ]] || { echo "$target already exists; stopping for review."; exit 1; }
netplan get ethernets.eth0 | python3 -c 'import sys,yaml; c=yaml.safe_load(sys.stdin); assert c == {"optional": True, "dhcp4": True}, "Ethernet configuration changed; review required"'
[[ $(cat /sys/class/net/eth0/address) == ${ETH0_MAC} ]] || exit 1
backup=$(mktemp -d /root/eth0-static-backup.XXXXXX)
cp -a /etc/netplan "$backup/netplan"
cat > "$backup/rollback.sh" <<'ROLLBACK'
#!/usr/bin/env bash
set -eu
rm -f /etc/netplan/99-eth0-static.yaml
netplan generate
networkctl reload
networkctl reconfigure eth0
ROLLBACK
chmod 700 "$backup/rollback.sh"
unit="eth0-static-rollback-$(date +%s)"
systemd-run --unit="$unit" --on-active=180s /bin/bash "$backup/rollback.sh"
rollback_on_error() {
  trap - ERR
  echo "Configuration failed; restoring DHCP. Backup: $backup"
  /bin/bash "$backup/rollback.sh" && systemctl stop "$unit.timer"
  exit 1
}
trap rollback_on_error ERR
umask 077
cat > "$target" <<YAML
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: false
      addresses:
        - ${PI_IPV4_CIDR}
      routes:
        - to: default
          via: ${LAN_GATEWAY}
          metric: 100
      nameservers:
        addresses:
          - ${LAN_GATEWAY}
        search:
          - lan
YAML
netplan generate
networkctl reload
networkctl reconfigure eth0
for attempt in {1..30}; do
  if ping -I eth0 -c 1 -W 2 ${LAN_GATEWAY} >/dev/null 2>&1 &&
     dig -b ${PI_IPV4} @${PI_IPV4} example.com +time=2 +tries=1 +short | grep -q . &&
     ip -4 address show wlan0 | grep -Fq "${RECOVERY_WIFI_CIDR}" &&
     ip -4 address show eth0 | grep -F "${PI_IPV4_CIDR}" | grep -qv dynamic &&
     ip -4 route show default dev eth0 | grep -F "via ${LAN_GATEWAY}" | grep -qv 'proto dhcp'; then
    break
  fi
  sleep 2
done
ping -I eth0 -c 2 -W 2 ${LAN_GATEWAY}
dig -b ${PI_IPV4} @${PI_IPV4} example.com +time=2 +tries=1 +short | grep .
ip -4 address show eth0 | grep -F "${PI_IPV4_CIDR}" | grep -v dynamic
ip -4 address show wlan0 | grep -F "${RECOVERY_WIFI_CIDR}"
ip -4 route show default dev eth0 | grep -F "via ${LAN_GATEWAY}" | grep -v 'proto dhcp'
systemctl stop "$unit.timer"
trap - ERR
echo "SUCCESS: eth0 static at ${PI_IPV4_CIDR}; gateway and Pi-hole DNS verified."
echo "Backup: $backup"
echo "Manual rollback: sudo bash $backup/rollback.sh"
