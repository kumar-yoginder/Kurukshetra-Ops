#!/usr/bin/env python3
"""Register one validated public peer in the gateway and private server config."""
import base64
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

if os.geteuid() != 0 or len(sys.argv) != 2:
    raise SystemExit('Usage: sudo python3 scripts/tor-gateway/register-peer.py PRIVATE_PEER_JSON')
root = Path(__file__).resolve().parents[2]
server = root / 'config/tor-gateway/wg0.conf'
if server.is_symlink() or server.stat().st_uid != 0:
    raise SystemExit('Expected a root-owned regular server configuration')
peer = json.loads(Path(sys.argv[1]).read_text())
key = peer['public_key']
if not re.fullmatch(r'[A-Za-z0-9+/]{43}=', key) or len(base64.b64decode(key, validate=True)) != 32:
    raise SystemExit('Invalid public key')
address = ipaddress.IPv4Address(peer['address'])
if address not in ipaddress.IPv4Network('10.77.0.0/24') or not 2 <= int(str(address).split('.')[-1]) <= 254:
    raise SystemExit('Invalid tunnel client address')
with open('/run/kurukshetra-peer-registration.lock', 'w') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    original = server.read_text()
    found = False
    for section in re.split(r'(?m)(?=^\[Peer\]\s*$)', original)[1:]:
        public = re.search(r'(?mi)^PublicKey\s*=\s*(\S+)\s*$', section)
        allowed = re.search(r'(?mi)^AllowedIPs\s*=\s*(.+)$', section)
        if not public or not allowed:
            raise SystemExit('Review malformed existing peer before registration')
        networks = [ipaddress.ip_network(value.strip()) for value in allowed[1].split(',')]
        if public[1] == key:
            if networks != [ipaddress.ip_network(str(address) + '/32')]:
                raise SystemExit('Public key already has a different assignment')
            found = True
        elif any(address in network for network in networks if network.version == 4):
            raise SystemExit('Tunnel address already assigned to another peer')
    updated = original if found else original.rstrip() + '\n\n[Peer]\nPublicKey = ' + key + '\nAllowedIPs = ' + str(address) + '/32\n'
    subprocess.run(['docker', 'exec', 'kurukshetra-ops-tor-gateway-1', 'wg', 'set', 'wg0',
                    'peer', key, 'allowed-ips', str(address) + '/32'], check=True)
    if updated != original:
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix='.wg-register-', dir=server.parent)
            with os.fdopen(fd, 'w') as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(updated)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, server)
        except BaseException:
            subprocess.run(['docker', 'exec', 'kurukshetra-ops-tor-gateway-1', 'wg', 'set', 'wg0', 'peer', key, 'remove'], check=False)
            raise
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
print('Peer registered persistently and in the running gateway. No service restarted.')
