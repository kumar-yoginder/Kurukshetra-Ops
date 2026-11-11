#!/usr/bin/env python3
"""Scheduled bounded home/Tor samples. Web requests cannot start probes."""
from pathlib import Path
import datetime
import fcntl
import json
import os
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
try:
    import pydantic
except ImportError:
    interpreter = root / ".venv-router/bin/python"
    if not interpreter.is_file():
        raise SystemExit("Configured monitoring Python environment is missing")
    os.execv(str(interpreter), [str(interpreter), __file__])
from network_speed import InternetProbe, SpeedReport, SpeedSample, TorProbeResult
from pydantic import ValidationError

with open(root / "config/nginx/www/.tor-probe.lock", "w") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(0)
    internet = InternetProbe().run()
    result = TorProbeResult(checked=datetime.datetime.now(datetime.timezone.utc), verified_tor=False, exit_ip=None, sample_bytes=262144, test_state="unavailable")
    try:
        process = subprocess.run(["docker", "exec", "-i", "kurukshetra-ops-tor-gateway-1", "python3", "-"], input=(root / "scripts/monitoring/tor-probe.py").read_text(), capture_output=True, text=True, timeout=120)
        if process.returncode == 0:
            result = TorProbeResult.model_validate_json(process.stdout)
            if not result.verified_tor:
                result.sample_mbps = result.upload_mbps = result.response_ms = None
                result.test_state = "unavailable"
    except (OSError, ValueError, subprocess.TimeoutExpired, ValidationError):
        pass
    tor = SpeedSample(checked=result.checked, test_state=result.test_state, download_mbps=result.sample_mbps, upload_mbps=result.upload_mbps, response_ms=result.response_ms, download_bytes=result.sample_bytes, upload_bytes=result.upload_bytes, verified_tor=result.verified_tor)
    report = SpeedReport(updated=datetime.datetime.now(datetime.timezone.utc), internet=internet, tor=tor)
    for filename, model in (("tor-metrics.json", result), ("speed-metrics.json", report)):
        fd, name = tempfile.mkstemp(prefix=".tor-metrics-", dir=root / "config/nginx/www")
        with os.fdopen(fd, "w") as output:
            output.write(model.model_dump_json(indent=2) + "\n")
            os.fchmod(output.fileno(), 0o644)
        os.replace(name, root / "config/nginx/www" / filename)
