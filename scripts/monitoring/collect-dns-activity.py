#!/usr/bin/env python3
"""Publish anonymous 24-hour DNS aggregates; never export addresses or domains."""
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def summarize(rows, now):
    clients = {}
    buckets = [0] * 24
    start = now - 86400
    for address, timestamp, count in rows:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        # Exclude local services, Docker bridges and non-LAN sources.
        if ip.version != 4 or not any(ip in net for net in (
                ipaddress.ip_network('192.168.0.0/16'),
                ipaddress.ip_network('10.0.0.0/8'))):
            continue
        timestamp, count = int(timestamp), int(count)
        if not start <= timestamp < now or count < 1:
            continue
        bucket = min(23, (timestamp - start) // 3600)
        buckets[bucket] += count
        entry = clients.setdefault(address, {'queries': 0, 'last_seen': timestamp})
        entry['queries'] += count
        entry['last_seen'] = max(entry['last_seen'], timestamp)
    # Rank labels intentionally do not identify or track a device across snapshots.
    ordered = sorted(clients.values(), key=lambda item: (-item['queries'], -item['last_seen']))
    return {
        'updated': dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(),
        'window_hours': 24, 'state': 'available', 'client_count': len(ordered),
        'queries': sum(buckets), 'hourly_queries': buckets,
        'clients': [{'name': f'Client {i}', 'queries': item['queries'],
                     'minutes_since_query': max(0, (now-item['last_seen']) // 60)}
                    for i, item in enumerate(ordered, 1)]
    }


def main():
    root = Path(__file__).resolve().parents[2]
    now = int(time.time())
    # One row per client and minute bounds output while preserving minute-level recency.
    sql = ('SELECT client, MAX(timestamp) AS last_seen, COUNT(*) AS queries FROM queries '
           f'WHERE timestamp >= {now-86400} AND timestamp < {now} '
           'GROUP BY client, CAST(timestamp / 60 AS INTEGER);')
    try:
        result = subprocess.run(['docker', 'exec', 'pihole', 'pihole-FTL', 'sqlite3',
            '-readonly', '-json', '/etc/pihole/pihole-FTL.db', sql],
            capture_output=True, text=True, timeout=25, check=True)
        raw = json.loads(result.stdout or '[]')
        rows = [(item['client'], item['last_seen'], item['queries']) for item in raw]
        payload = summarize(rows, now)
        payload['source'] = 'Persisted Pi-hole DNS records; recent writes may be delayed'
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        payload = {'updated': dt.datetime.now(dt.timezone.utc).isoformat(),
                   'state': 'unavailable', 'window_hours': 24}
    directory = root / 'config/nginx/www'
    fd, name = tempfile.mkstemp(prefix='.dns-', dir=directory)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            os.fchmod(stream.fileno(), 0o644)
        os.replace(name, directory / 'dns-activity.json')
    finally:
        if os.path.exists(name):
            os.unlink(name)


    # Separate owner-only IP counters for the private inventory container.
    if payload.get("state")=="available":
        counts={}
        for address,timestamp,count in rows:
            try: address=str(ipaddress.ip_address(address))
            except ValueError: continue
            counts[address]=counts.get(address,0)+int(count)
        private=root / "data/dns-activity"
        private.mkdir(parents=True,exist_ok=True,mode=0o700)
        private.chmod(0o700)
        fd,name=tempfile.mkstemp(dir=private,prefix=".counts-")
        try:
            with os.fdopen(fd,"w") as stream:
                os.fchmod(stream.fileno(),0o600)
                json.dump({"updated":now,"counts":counts},stream,indent=2,ensure_ascii=False);stream.write("\n")
            os.replace(name,private/"dns-counts.json")
        finally:
            if os.path.exists(name):os.unlink(name)

if __name__ == '__main__':
    main()
