#!/usr/bin/env python3
"""Publish only allowlisted service names and basic states; never Docker metadata."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
services = [('Pi-hole', 'pihole'), ('HTTPS gateway', 'kurukshetra-gateway'),
            ('Certificate service', 'cert-gen'), ('Tor gateway', 'kurukshetra-ops-tor-gateway-1'),
            ('Chitragupt', 'chitragupt_bot'), ('Central identity', 'kurukshetra-ops-identity-1'),
            ('Web application firewall', 'kurukshetra-ops-gateway-waf-1'),
            ('Private inventory', 'kurukshetra-ops-router-inventory-1'),
            ('Pi-hole session bridge', 'kurukshetra-ops-pihole-bridge-1'),
            ('Application router', 'kurukshetra-ops-web-router-1'), ('Grafana', 'kurukshetra-ops-grafana-1'), ('Prometheus', 'kurukshetra-ops-prometheus-1'), ('Grafana Alloy', 'kurukshetra-ops-alloy-1'), ('Elasticsearch', 'elasticsearch'),
            ('Kibana', 'kibana'), ('Filebeat', 'filebeat')]
rows = []
for label, container in services:
    state = 'unknown'
    try:
        result = subprocess.run(['docker', 'inspect', '--format',
            '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}', container],
            capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            runtime, health = result.stdout.strip().split('|', 1)
            state = ('healthy' if health == 'healthy' else 'unhealthy' if health == 'unhealthy'
                     else 'starting' if health == 'starting' else 'running') if runtime == 'running' else 'stopped'
        elif 'no such' in result.stderr.lower():
            state = 'not-deployed'
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    rows.append({'name': label, 'state': state})
peers = []
peer_state = 'unknown'
try:
    result = subprocess.run(['docker', 'exec', 'kurukshetra-ops-tor-gateway-1', 'wg', 'show', 'wg0', 'latest-handshakes'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        for number, line in enumerate(sorted(result.stdout.splitlines()), 1):
            key, timestamp = line.split()
            age = max(0, int(now - int(timestamp))) if int(timestamp) else None
            peers.append({'name': 'Peer ' + str(number), 'recent': age is not None and age <= 180,
                          'handshake_age_seconds': age})
        peer_state = 'available'
except (OSError, ValueError, subprocess.TimeoutExpired):
    pass
payload = {'updated': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'services': rows,
           'tor': {'peers': peers, 'peer_state': peer_state}}
directory = root / 'config/nginx/www'
fd, temporary = tempfile.mkstemp(prefix='.status-', dir=directory)
try:
    with os.fdopen(fd, 'w') as output:
        json.dump(payload, output, indent=2, ensure_ascii=False)
        output.write('\n')
        os.fchmod(output.fileno(), 0o644)
    os.replace(temporary, directory / 'status.json')
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)

# DNS collection failure never blocks the existing service summary.
try:
    subprocess.run(["/usr/bin/python3", str(root / "scripts/monitoring/collect-dns-activity.py")], timeout=30, check=False)
except (OSError, subprocess.TimeoutExpired):
    pass

# Read-only integration; the bot lifecycle remains in its separate Compose project.
try:
    subprocess.run(["/usr/bin/python3", str(root / "scripts/monitoring/collect-chitragupt.py")], timeout=15, check=False)
except (OSError, subprocess.TimeoutExpired):
    pass

# Safe host telemetry is optional; missing tools must not stop the status page.
try:
    subprocess.run(["/usr/bin/python3", str(root / "scripts/monitoring/collect-observability.py")], timeout=20, check=False)
except (OSError, subprocess.TimeoutExpired):
    pass

# Bounded sanitized operational events; reuse the existing minute schedule.
try:
    subprocess.run(["/usr/bin/python3", str(root / "scripts/monitoring/collect-logs.py")], timeout=28, check=False)
except (OSError, subprocess.TimeoutExpired):
    pass
