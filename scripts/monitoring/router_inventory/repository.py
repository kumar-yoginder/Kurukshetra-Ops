"""Owner-only local state with bounded observation retention."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from .models import Inventory, HistoryRecord

def atomic_json(path:Path,data:dict):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.inventory-')
    try:
        with os.fdopen(fd,'w') as stream:
            os.fchmod(stream.fileno(),0o600);json.dump(data,stream,indent=2,ensure_ascii=False);stream.write('\n')
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

class InventoryRepository:
    def __init__(self,directory:Path):
        self.directory=directory
        directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        directory.chmod(0o700)
        self.snapshot=directory/'inventory.json'

    def observe(self,devices,now):
        db=sqlite3.connect(self.directory/'history.sqlite3',timeout=5)
        try:
            with db:
                db.execute('CREATE TABLE IF NOT EXISTS observations (timestamp INTEGER, mac TEXT, name TEXT, kind TEXT, wifi INTEGER)')
                db.execute('CREATE INDEX IF NOT EXISTS observations_time ON observations(timestamp)')
                db.executemany('INSERT INTO observations VALUES (?,?,?,?,?)',[(now,d.mac,d.name,d.type,int(d.wifi_connected)) for d in devices])
                db.execute('DELETE FROM observations WHERE timestamp < ?',(now-86400,))
                return [HistoryRecord(mac=mac,name=name,type=kind,first_observed=first,last_observed=last,wifi_observations=wifi)
                    for mac,name,kind,first,last,wifi in db.execute('SELECT mac,MAX(name),MAX(kind),MIN(timestamp),MAX(timestamp),SUM(wifi) FROM observations GROUP BY mac')]
        finally:db.close()

    def publish(self,inventory:Inventory):atomic_json(self.snapshot,inventory.model_dump(mode='json'))

    def unavailable(self,now,message):
        try:previous=Inventory.model_validate_json(self.snapshot.read_text())
        except (OSError,ValueError):previous=Inventory(state='unavailable')
        previous.state='unavailable';previous.attempted=now;previous.error=message
        self.publish(previous)
