#!/usr/bin/env python3
"""Bounded operational log events. Raw messages never leave process memory."""
import fcntl
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from typing import Literal
ROOT = Path(__file__).resolve().parents[2]
try:
    from pydantic import BaseModel, ConfigDict, Field
except ImportError:
    os.execv(str(ROOT / '.venv-router/bin/python'), [str(ROOT / '.venv-router/bin/python'), __file__])
SERVICES = {
    'chitragupt': 'chitragupt_bot', 'gateway': 'kurukshetra-gateway',
    'identity': 'kurukshetra-ops-identity-1', 'waf': 'kurukshetra-ops-gateway-waf-1',
    'inventory': 'kurukshetra-ops-router-inventory-1', 'tor': 'kurukshetra-ops-tor-gateway-1',
    'grafana': 'kurukshetra-ops-grafana-1', 'prometheus': 'kurukshetra-ops-prometheus-1',
    'alloy': 'kurukshetra-ops-alloy-1', 'pihole': 'pihole',
}
Service = Literal['chitragupt','gateway','identity','waf','inventory','tor','grafana','prometheus','alloy','pihole']
Level = Literal['info','warning','error','critical']
Kind = Literal['informational','warning','error','critical','timeout','connection_failure','authentication_failure','startup']
class Event(BaseModel):
    model_config = ConfigDict(extra='forbid')
    timestamp: datetime
    service: Service
    level: Level
    kind: Kind
class Source(BaseModel):
    model_config = ConfigDict(extra='forbid')
    service: Service
    state: Literal['available','unavailable','bounded']
    omitted_lines: int = Field(ge=0)
class Snapshot(BaseModel):
    model_config = ConfigDict(extra='forbid')
    updated: datetime
    events: list[Event] = Field(max_length=2000)
    sources: list[Source] = Field(max_length=10)
    retention_hours: Literal[24] = 24
    limit: Literal[2000] = 2000

def classify(line, service):
    """Emit only enums and Docker timestamps, never text extracted from messages."""
    stamp, _, message = line.partition(' ')
    try:
        # Docker timestamps have nanoseconds. Trim to Python microseconds.
        timestamp = datetime.fromisoformat(re.sub(r'(\.\d{6})\d+',r'\1',stamp).replace('Z','+00:00'))
        if timestamp.tzinfo is None:
            return None
    except ValueError:
        return None
    text = message[:8192].lower()
    level = next((value for value, pattern in [
        ('critical', r'\b(critical|fatal|panic)\b'),
        ('error', r'\b(error|exception|traceback|failed|failure)\b'),
        ('warning', r'\b(warn|warning)\b'),
        ('info', r'\b(info|information|notice)\b'),
    ] if re.search(pattern,text)), None)
    if level is None:
        return None
    kind = {'info':'informational','warning':'warning','error':'error','critical':'critical'}[level]
    if re.search(r'\b(timed out|timeout|timeouterror)\b',text): kind='timeout'
    elif re.search(r'\b(connection refused|connection reset|connectionerror)\b',text): kind='connection_failure'
    elif re.search(r'\b(unauthorized|authentication failed|invalid credentials)\b',text): kind='authentication_failure'
    elif re.search(r'\b(started|starting|listening|ready)\b',text): kind='startup'
    return Event(timestamp=timestamp,service=service,level=level,kind=kind)

def bounded_read(command, cap=262144, seconds=2):
    proc = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    data=bytearray(); clipped=False
    try:
        with selectors.DefaultSelector() as poll:
            poll.register(proc.stdout,selectors.EVENT_READ)
            until=time.monotonic()+seconds
            while time.monotonic()<until:
                if not poll.select(max(0,until-time.monotonic())): break
                chunk=os.read(proc.stdout.fileno(),min(8192,cap-len(data)+1))
                if not chunk:
                    proc.wait(timeout=0.5)
                    return bytes(data).decode('utf-8','replace'),proc.returncode,clipped
                data.extend(chunk)
                if len(data)>cap:
                    clipped=True;break
        proc.kill();proc.wait(timeout=1)
        return bytes(data[:cap]).decode('utf-8','replace'),-1,True
    finally:
        if proc.poll() is None: proc.kill();proc.wait(timeout=1)
        proc.stdout.close()

def atomic(path, text, mode=0o600):
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.logs-')
    try:
        with os.fdopen(fd,'w') as output:
            os.fchmod(output.fileno(),mode);output.write(text)
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def retained(events, now):
    cutoff=now-timedelta(hours=24)
    unique={(e.timestamp,e.service,e.level,e.kind):e for e in events if cutoff<=e.timestamp<=now}
    return sorted(unique.values(),key=lambda e:e.timestamp)[-2000:]

def main():
    private=ROOT/'config/observability/private/logs';private.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (private/'lock').open('w') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        now=datetime.now(timezone.utc); cutoff=now-timedelta(hours=24)
        public=ROOT/'config/nginx/www/log-events.json'
        try: old=Snapshot.model_validate_json(public.read_text());events=[e for e in old.events if cutoff<=e.timestamp<=now]
        except (ValueError,OSError):events=[]
        try: cursors=json.loads((private/'cursors.json').read_text())
        except (ValueError,OSError):cursors={}
        sources=[]
        for service,container in SERVICES.items():
            try:
                since=datetime.fromisoformat(cursors[service]);since=max(since,cutoff)
                if since>now:since=now-timedelta(minutes=5)
            except (ValueError,KeyError,TypeError):since=now-timedelta(minutes=5)
            text,code,clipped=bounded_read(['docker','logs','--timestamps','--tail','200','--since',since.isoformat(),'--until',now.isoformat(),container])
            lines=text.splitlines(); omitted=0
            if code==0 or clipped:
                for line in lines:
                    event=classify(line,service)
                    if event and since<=event.timestamp<=now:events.append(event)
                    else:omitted+=1
                cursors[service]=now.isoformat()
            sources.append(Source(service=service,state='bounded' if clipped or len(lines)>=200 else 'available' if code==0 else 'unavailable',omitted_lines=omitted))
        # Deduplicate inclusive cursor boundaries; no hashes of private text are persisted.
        events=retained(events,now)
        snapshot=Snapshot(updated=now,events=events,sources=sources)
        atomic(public,snapshot.model_dump_json(indent=2)+'\n',0o644)
        atomic(private/'cursors.json',json.dumps(cursors,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':main()
