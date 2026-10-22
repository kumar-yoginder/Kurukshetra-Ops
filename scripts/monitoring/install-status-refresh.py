#!/usr/bin/env python3
"""Install an idempotent per-user minute schedule without replacing other jobs."""
from pathlib import Path
import shlex
import subprocess
root = Path(__file__).resolve().parents[2]
marker = "# kurukshetra-public-status"
result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
if result.returncode not in (0, 1) or (result.returncode == 1 and "no crontab" not in result.stderr.lower()):
    raise SystemExit("Cannot safely read existing crontab")
lines = [line for line in result.stdout.splitlines() if not line.endswith(marker) and not line.endswith("# kurukshetra-tor-metrics")]
command = "* * * * * /usr/bin/python3 " + shlex.quote(str(root / "scripts/monitoring/collect-status.py")) + " >/dev/null 2>&1 " + marker
lines.append(command)
lines.append("*/15 * * * * /usr/bin/python3 " + shlex.quote(str(root / "scripts/monitoring/collect-tor-metrics.py")) + " >/dev/null 2>&1 # kurukshetra-tor-metrics")
subprocess.run(["/usr/bin/python3", str(root / "scripts/tor-client/publish-downloads.py")], check=True)
subprocess.run(["crontab", "-"], input="\n".join(lines)+"\n", text=True, check=True)
subprocess.run(["/usr/bin/python3", str(root / "scripts/monitoring/collect-status.py")], check=True)
print("Public status refresh installed: every minute, current user, read-only collector")
