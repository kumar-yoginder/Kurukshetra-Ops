#!/usr/bin/env python3
"""Bounded scheduled probe. Public callers cannot trigger commands or downloads."""
from pathlib import Path
import datetime
import fcntl
import json
import os
import subprocess
import tempfile
root = Path(__file__).resolve().parents[2]
lock = open(root / "config/nginx/www/.tor-probe.lock", "w")
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)
result = {"checked": datetime.datetime.now(datetime.timezone.utc).isoformat(), "verified_tor": False,
          "exit_ip": None, "sample_mbps": None, "response_ms": None, "sample_bytes": 262144,
          "test_state": "unavailable"}
try:
    process = subprocess.run(["docker", "exec", "-i", "kurukshetra-ops-tor-gateway-1", "python3", "-"],
        input=(root / "scripts/monitoring/tor-probe.py").read_text(), capture_output=True, text=True, timeout=90)
    if process.returncode == 0:
        value = json.loads(process.stdout)
        if set(value) == set(result):
            result = value
except (OSError, ValueError, subprocess.TimeoutExpired):
    pass
fd, name = tempfile.mkstemp(prefix=".tor-metrics-", dir=root / "config/nginx/www")
with os.fdopen(fd, "w") as output:
    json.dump(result, output)
    os.fchmod(output.fileno(), 0o644)
os.replace(name, root / "config/nginx/www/tor-metrics.json")
