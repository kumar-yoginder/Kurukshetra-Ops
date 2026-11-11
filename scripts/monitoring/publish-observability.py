#!/usr/bin/env python3
"""Render reviewed dashboard templates with a private canonical portal origin."""
import json
import os
from pathlib import Path
import re
import tempfile
ROOT = Path(__file__).resolve().parents[2]
host = next(line.split("=", 1)[1] for line in (ROOT / ".env").read_text().splitlines() if line.startswith("GATEWAY_HOST="))
if not re.fullmatch(r"[a-zA-Z0-9.-]+", host):
    raise SystemExit("Invalid configured gateway hostname")
target = ROOT / "config/observability/private/dashboards"
target.mkdir(parents=True, exist_ok=True, mode=0o700)
target.chmod(0o700)
for source in sorted((ROOT / "config/observability/grafana/dashboards").glob("*.json")):
    value = json.loads(source.read_text().replace("__PORTAL_ORIGIN__", "https://" + host))
    fd, temporary = tempfile.mkstemp(dir=target)
    with os.fdopen(fd, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, target / source.name)
print("Published configured local dashboards")
