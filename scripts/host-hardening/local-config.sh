#!/usr/bin/env bash
# Sourced only by the host-hardening utilities.
site_config="$source_dir/../../config/host-hardening/local.env"
[[ -f "$site_config" ]] || { echo 'Missing config/host-hardening/local.env; see documentation.' >&2; exit 1; }
source "$site_config"
: "${HARDENING_USER:?}" "${PI_IPV4_CIDR:?}" "${PI_IPV4:?}" "${LAN_GATEWAY:?}" "${RECOVERY_WIFI_CIDR:?}" "${ETH0_MAC:?}" "${LAN_IPV6_PREFIX:?}" "${LAN_IPV6_MATCH:?}"
python3 - "$HARDENING_USER" "$PI_IPV4_CIDR" "$PI_IPV4" "$LAN_GATEWAY" "$RECOVERY_WIFI_CIDR" "$ETH0_MAC" "$LAN_IPV6_PREFIX" "$LAN_IPV6_MATCH" <<'VALIDATE'
import ipaddress,re,sys
user,cidr,address,gateway,wifi,mac,prefix,match=sys.argv[1:]
assert re.fullmatch(r'[a-z_][a-z0-9_-]*', user), 'Invalid local username'
assert ipaddress.IPv4Interface(cidr).ip == ipaddress.IPv4Address(address), 'Address/CIDR mismatch'
ipaddress.IPv4Address(gateway); ipaddress.IPv4Interface(wifi)
assert re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}',mac), 'Invalid MAC'
ipaddress.IPv6Network(prefix)
assert re.fullmatch(r'[0-9a-fA-F:]+',match), 'Invalid IPv6 match'
VALIDATE
