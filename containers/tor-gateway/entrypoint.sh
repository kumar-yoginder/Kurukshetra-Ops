#!/bin/sh
set -eu
umask 077
[ -s /run/wireguard/wg0.conf ] || { echo 'Missing private WireGuard server configuration' >&2; exit 1; }
mkdir -p /var/lib/tor
chown debian-tor:debian-tor /var/lib/tor
chmod 700 /var/lib/tor
tor_uid=$(id -u debian-tor)
sed "s/@TOR_UID@/$tor_uid/g" /usr/local/share/tor-gateway/firewall.nft.in > /tmp/tor-gateway.nft
# Install restrictions before creating or exposing the tunnel interface.
nft -c -f /tmp/tor-gateway.nft
nft -f /tmp/tor-gateway.nft
ip link add wg0 type wireguard
wg setconf wg0 /run/wireguard/wg0.conf
# Fixed internal test subnet; validate absence of conflicts before deployment.
ip address add 10.77.0.1/24 dev wg0
ip link set wg0 mtu 1380 up
# Peers must use /32 AllowedIPs within this subnet; no forwarding/NAT route exists.
tor --verify-config -f /etc/tor/torrc
exec tor -f /etc/tor/torrc
