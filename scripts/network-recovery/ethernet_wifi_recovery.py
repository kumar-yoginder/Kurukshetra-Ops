#!/usr/bin/env python3
"""Ethernet-preferred Wi-Fi recovery; status is the default, no mutation."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time


def command(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=8)


def carrier(interface):
    try:
        return Path('/sys/class/net', interface, 'carrier').read_text().strip() == '1'
    except OSError:
        return False


def admin_up(interface):
    try:
        return bool(int(Path('/sys/class/net', interface, 'flags').read_text().strip(), 16) & 1)
    except OSError:
        return False


class Decision:
    def __init__(self, fail=3, recover=6):
        self.fail, self.recover = fail, recover
        self.bad = self.good = 0

    def sample(self, healthy, wifi_up):
        self.bad = 0 if healthy else min(self.bad + 1, self.fail)
        self.good = min(self.good + 1, self.recover) if healthy else 0
        if not healthy and self.bad >= self.fail and not wifi_up:
            return 'up'
        if healthy and self.good >= self.recover and wifi_up:
            return 'down'
        return None


def load(path):
    c = json.loads(Path(path).read_text())
    for key in ('ethernet', 'wifi'):
        if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', c[key]):
            raise ValueError('invalid interface')
    if c['ethernet'] == c['wifi']:
        raise ValueError('interfaces must differ')
    ipaddress.IPv4Address(c['router_ipv4'])
    for key, low, high in [('interval_seconds', 3, 300), ('failure_samples', 2, 100), ('recovery_samples', 2, 100)]:
        if type(c[key]) is not int or not low <= c[key] <= high:
            raise ValueError('invalid ' + key)
    return c


def healthy(c):
    # Bind probes to Ethernet: a successful Wi-Fi path must never count as Ethernet recovery.
    return carrier(c['ethernet']) and command([
        'ping', '-n', '-I', c['ethernet'], '-c', '1', '-W', '2', c['router_ipv4']
    ]).returncode == 0



class WifiPolicy:
    """Reserve table/priority 10421 for same-subnet replies only; leave Internet routes alone."""
    TABLE = '10421'
    STATE = Path('/run/kurukshetra-network-recovery-policy.json')

    def __init__(self, wifi):
        self.wifi = wifi
        self.previous = None
        if self.STATE.exists():
            self.previous = json.loads(self.STATE.read_text())
            if self.previous['wifi'] != wifi:
                raise RuntimeError('existing recovery policy uses another interface')
        else:
            rules = command(['ip', '-j', '-4', 'rule', 'show'])
            routes = command(['ip', '-j', '-4', 'route', 'show', 'table', self.TABLE])
            if rules.returncode:
                raise RuntimeError('cannot inspect recovery policy rules')
            if routes.returncode:
                # iproute2 can emit incomplete JSON ('[') for a table not yet created.
                # Only that precise absent-table result is safe to treat as empty.
                if routes.returncode == 2 and 'FIB table does not exist.' in routes.stderr:
                    route_entries = []
                else:
                    raise RuntimeError('cannot inspect reserved recovery route table')
            else:
                route_entries = json.loads(routes.stdout or '[]')
            if any(str(r.get('priority')) == self.TABLE or str(r.get('table')) == self.TABLE
                   for r in json.loads(rules.stdout or '[]')) or route_entries:
                raise RuntimeError('reserved recovery rule/table already occupied')

    def sync(self):
        r = command(['ip', '-j', '-4', 'addr', 'show', 'dev', self.wifi])
        interfaces = json.loads(r.stdout or '[]')
        addresses = [a for i in interfaces for a in i.get('addr_info', [])
                     if a.get('scope') == 'global' and a.get('family') == 'inet']
        if not addresses:
            return False
        a = addresses[0]
        address = str(ipaddress.IPv4Address(a['local']))
        subnet = str(ipaddress.IPv4Network(address + '/' + str(a['prefixlen']), strict=False))
        current = {'wifi': self.wifi, 'address': address, 'subnet': subnet}
        if self.previous and self.previous != current:
            old = self.previous
            command(['ip', '-4', 'rule', 'del', 'priority', self.TABLE,
                     'from', old['address'] + '/32', 'lookup', self.TABLE])
            command(['ip', '-4', 'route', 'del', 'table', self.TABLE,
                     old['subnet'], 'dev', self.wifi])
            self.previous = None
        route = command(['ip', '-4', 'route', 'replace', 'table', self.TABLE,
                         subnet, 'dev', self.wifi, 'src', address])
        if route.returncode:
            raise RuntimeError('cannot establish Wi-Fi recovery reply route')
        # Persist ownership before adding the rule, allowing safe restart after interruption.
        self.STATE.write_text(json.dumps(current))
        rules = json.loads(command(['ip', '-j', '-4', 'rule', 'show']).stdout or '[]')
        matches = [r for r in rules if str(r.get('priority')) == self.TABLE]
        if matches and not all(r.get('src') in (address, address + '/32') and
                               str(r.get('table')) == self.TABLE for r in matches):
            raise RuntimeError('recovery priority conflict')
        if not matches:
            result = command(['ip', '-4', 'rule', 'add', 'priority', self.TABLE,
                              'from', address + '/32', 'lookup', self.TABLE])
            if result.returncode:
                raise RuntimeError('cannot establish Wi-Fi recovery source rule')
        self.previous = current
        return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='/etc/kurukshetra-network-recovery.json')
    p.add_argument('--monitor', action='store_true', help='root only; changes Wi-Fi administrative state')
    p.add_argument('--restore', action='store_true', help='root only; emergency Wi-Fi up and reply policy refresh')
    p.add_argument('--status', action='store_true', help='read-only (default)')
    a = p.parse_args()
    if sum((a.monitor, a.status, a.restore)) > 1:
        p.error('choose status or monitor')
    c = load(a.config)
    if a.restore:
        if os.geteuid() != 0:
            p.error('restore requires root')
        command(['networkctl', 'up', c['wifi']])
        policy = WifiPolicy(c['wifi'])
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if policy.sync():
                print('Wi-Fi requested up; IPv4 reply policy ready (association not verified)', flush=True)
                return
            time.sleep(2)
        raise RuntimeError('Wi-Fi requested up but no IPv4 address yet; inspect local console')
    if not a.monitor:
        print(json.dumps({'ethernet_carrier': carrier(c['ethernet']),
                          'ethernet_router_reachable': healthy(c),
                          'wifi_admin_up': admin_up(c['wifi'])}))
        return
    if os.geteuid() != 0:
        p.error('monitor requires root')
    import fcntl
    lock = open('/run/kurukshetra-network-recovery.lock', 'w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    policy = None
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    d = Decision(c['failure_samples'], c['recovery_samples'])
    try:
        policy = WifiPolicy(c['wifi'])
        while not stopped:
            if admin_up(c['wifi']):
                policy.sync()
            action = d.sample(healthy(c), admin_up(c['wifi']))
            if stopped:
                break
            if action:
                r = command(['networkctl', action, c['wifi']])
                print('wifi ' + action + (' requested' if r.returncode == 0 else ' FAILED'), flush=True)
            deadline = time.monotonic() + c['interval_seconds']
            while not stopped and time.monotonic() < deadline:
                time.sleep(0.25)
    finally:
        # Stopping the monitor always restores Wi-Fi as the conservative rollback.
        if not admin_up(c['wifi']):
            try:
                command(['networkctl', 'up', c['wifi']])
            except subprocess.TimeoutExpired:
                print('Wi-Fi restore command timed out; inspect interface locally', flush=True)
        # Preserve the source rule on shutdown: removing it could strand emergency SSH.
        for _ in range(3 if policy else 0):
            try:
                if policy.sync():
                    break
            except (RuntimeError, subprocess.TimeoutExpired):
                pass
            time.sleep(1)
        print('stopped; active Wi-Fi preserved for recovery', flush=True)


if __name__ == '__main__':
    main()
