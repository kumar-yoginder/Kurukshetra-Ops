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
            ('Bot', 'chitragupt_bot'), ('Elasticsearch', 'elasticsearch'),
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
        json.dump(payload, output)
        output.write('\n')
        os.fchmod(output.fileno(), 0o644)
    os.replace(temporary, directory / 'status.json')
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
