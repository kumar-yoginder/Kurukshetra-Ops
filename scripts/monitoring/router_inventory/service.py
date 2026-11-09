"""Collect router observations and join private Pi-hole aggregates."""
import ipaddress
import json
import os
import re
from pathlib import Path
import subprocess
import time
from .client import RouterClient, AuthenticationRequired, LoginRejected
from .models import RouterConfig, Device, Inventory
from .repository import InventoryRepository, atomic_json

class DeviceAssembler:
    @staticmethod
    def classify(name):
        value=name.casefold()
        for term,label in [('iphone','iPhone / likely iOS'),('ipad','iPad / likely iPadOS'),('mac','Mac / likely macOS'),('android','Likely Android'),('windows','Likely Windows')]:
            if term in value:return label,'hostname hint'
        return 'Unknown','unclassified'

    def merge(self,lan,wlan,dns):
        devices={}
        for row in lan:
            name=row.hostName.strip() or 'Unnamed device'
            if name.casefold()=='not available':name='Unnamed device'
            addresses=[]
            for value in re.split(r'[,\s]+',row.ipv4Address+' '+row.ipv6Address):
                try:addresses.append(str(ipaddress.ip_address(value)))
                except ValueError:pass
            kind,evidence=self.classify(name)
            devices[row.macAddress]=Device(mac=row.macAddress,name=name,addresses=addresses,type=kind,
                type_evidence=evidence,private_mac=bool(int(row.macAddress[:2],16)&2),
                dns_queries_24h=sum(dns.get(ip,0) for ip in addresses))
        for row in wlan:
            if row.macAddress not in devices:
                devices[row.macAddress]=Device(mac=row.macAddress,name='Unnamed Wi-Fi device',addresses=[],type='Unknown',
                    type_evidence='unclassified',private_mac=bool(int(row.macAddress[:2],16)&2),dns_queries_24h=0)
            devices[row.macAddress].wifi_connected=True;devices[row.macAddress].radio=row.radio
        return list(devices.values())

class DnsActivityClient:
    def read(self,now):
        private_counts=os.environ.get('PRIVATE_DNS_COUNTS_FILE')
        if private_counts:
            try:
                snapshot=json.loads(Path(private_counts).read_text())
                if now-snapshot['updated']>180:raise ValueError('stale DNS counters')
                return {str(ipaddress.ip_address(ip)):int(count) for ip,count in snapshot['counts'].items()},True
            except (OSError,ValueError,KeyError,TypeError):return {},False
        sql=f'SELECT client, COUNT(*) AS queries FROM queries WHERE timestamp >= {now-86400} AND timestamp < {now} GROUP BY client;'
        try:
            result=subprocess.run(['docker','exec','pihole','pihole-FTL','sqlite3','-readonly','-json','/etc/pihole/pihole-FTL.db',sql],capture_output=True,text=True,timeout=20,check=True)
            return {str(r['client']):int(r['queries']) for r in json.loads(result.stdout or '[]')},True
        except (OSError,ValueError,KeyError,subprocess.SubprocessError):return {},False

class InventoryCollector:
    def __init__(self,root:Path):
        self.root=root;self.repository=InventoryRepository(root/'data/router-inventory')

    def run(self):
        now=int(time.time());pause=self.repository.directory/'auth-paused.json'
        try:
            config_path=self.root/'config/router-inventory/local.json'
            if config_path.stat().st_mode & 0o077:raise ValueError('config must be owner-only')
            config=RouterConfig.model_validate_json(config_path.read_text())
            stamp=(config.password_file.stat().st_mtime_ns if config.password_file else config.token_file.stat().st_mtime_ns)
            if pause.exists() and json.loads(pause.read_text()).get('session_mtime_ns')==stamp:
                self.repository.unavailable(now,'Session expired. Refresh the private guest session to resume polling.')
                return 1
            client=RouterClient(config)
            try:lan,wlan=client.read_devices()
            except (AuthenticationRequired,LoginRejected):
                client.login()
                lan,wlan=client.read_devices()
            dns,available=DnsActivityClient().read(now)
            devices=DeviceAssembler().merge(lan,wlan,dns)
            history=self.repository.observe(devices,now)
            self.repository.publish(Inventory(updated=now,state='available',devices=devices,history=history,dns_available=available))
            pause.unlink(missing_ok=True)
            print('Private inventory refreshed:',len(devices),'records')
            return 0
        except (AuthenticationRequired,LoginRejected):
            atomic_json(pause,{'session_mtime_ns':stamp})
            self.repository.unavailable(now,'Session expired. Refresh the private guest session to resume polling.')
        except Exception:
            # Never print validation inputs: they can contain session or device data.
            self.repository.unavailable(now,'Collection unavailable. Check local configuration, pinned router identity and connectivity.')
        print('Private inventory unavailable; previous observation retained.')
        return 1
