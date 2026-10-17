#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
# An exported PIHOLE_LAN_IP overrides discovery. NETWORK_INTERFACE selects a NIC.
python3 - <<'PYNET'
import ipaddress,json,os,re,subprocess
from pathlib import Path
def ip(*args):
    return json.loads(subprocess.check_output(["ip","-j",*args],text=True))
address=os.environ.get("PIHOLE_LAN_IP","")
if not address:
    interface=os.environ.get("NETWORK_INTERFACE","")
    if not interface:
        routes=[r for r in ip("-4","route","show","default") if r.get("dev")]
        if not routes:
            raise SystemExit("No IPv4 default route: set NETWORK_INTERFACE or PIHOLE_LAN_IP.")
        interface=min(routes,key=lambda r:r.get("metric",0))["dev"]
    addresses=[a["local"] for item in ip("-4","addr","show","dev",interface)
               for a in item.get("addr_info",[]) if a.get("scope")=="global"]
    if len(addresses)!=1:
        raise SystemExit("Expected one IPv4 address on "+interface+"; set PIHOLE_LAN_IP explicitly.")
    address=addresses[0]
v=ipaddress.ip_address(address)
if v.version!=4 or v.is_loopback or v.is_unspecified or v.is_multicast or v.is_link_local:
    raise SystemExit("PIHOLE_LAN_IP must be a usable LAN IPv4 address.")
p=Path(".env")
s=p.read_text() if p.exists() else ""
line="PIHOLE_LAN_IP="+address
if re.search(r"^PIHOLE_LAN_IP=.*$",s,re.M):
    s=re.sub(r"^PIHOLE_LAN_IP=.*$",line,s,flags=re.M)
else:
    s=s.rstrip()+"\n"+line+"\n"
temporary=Path(".env.network-tmp")
fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,"w") as f:
    f.write(s)
os.replace(temporary,p)
print("Pi-hole LAN address:",address)
PYNET
docker compose config --quiet
if [[ "${1:-}" == "--configure-only" ]]; then
    exit 0
fi
if [[ $# -eq 0 ]]; then
    set -- up -d
fi
exec docker compose "$@"
