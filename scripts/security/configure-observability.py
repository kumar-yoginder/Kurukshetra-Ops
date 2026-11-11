#!/usr/bin/env python3
"""Prepare private Grafana origin/trusted-proxy configuration, without starting services."""
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import sys
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]

def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True)

def write(text):
    directory = ROOT / "config/observability/private"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    fd, name = tempfile.mkstemp(dir=directory)
    with os.fdopen(fd, "w") as out:
        os.fchmod(out.fileno(), 0o644)
        out.write(text)
    os.replace(name, directory / "grafana.ini")

host = next(line.split("=", 1)[1] for line in (ROOT / ".env").read_text().splitlines() if line.startswith("GATEWAY_HOST="))
if not re.fullmatch(r"[a-zA-Z0-9.-]+", host):
    raise SystemExit("Invalid configured gateway hostname")
secret = ROOT / "config/observability/private/secrets/grafana_key"
secret.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
secret.parent.chmod(0o700)
if not secret.exists():
    fd = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(secrets.token_urlsafe(48))
if secret.stat().st_mode & 0o077:
    raise SystemExit("Grafana secret file must be owner-only")
template = (ROOT / "config/observability/grafana.ini.template").read_text().replace("__GATEWAY_HOST__", host)
subprocess.run([sys.executable, str(ROOT / "scripts/monitoring/publish-observability.py")], cwd=ROOT, check=True)
# Deny proxy login while networks are only being prepared.
write(template.replace("__AUTH_PROXY_CIDR__", "127.0.0.1/32"))
subprocess.run(["docker", "compose", "--profile", "observability", "create", "observability-init", "prometheus", "alloy", "grafana"], cwd=ROOT, check=True)
info = json.loads(run("docker", "compose", "--profile", "observability", "ps", "-a", "--format", "json", "grafana"))
container = info["ID"] if isinstance(info, dict) else info[0]["ID"]
metadata = json.loads(run("docker", "inspect", container))[0]
selected = None
for name in metadata["NetworkSettings"]["Networks"]:
    network = json.loads(run("docker", "network", "inspect", name))[0]
    if network.get("Labels", {}).get("com.docker.compose.network") == "observability-gateway":
        if not network["Internal"]:
            raise SystemExit("Grafana authentication network must be internal")
        selected = next(str(ipaddress.ip_network(v["Subnet"])) for v in network["IPAM"]["Config"] if ":" not in v["Subnet"])
if selected is None:
    raise SystemExit("Isolated gateway network not found; refusing broad proxy trust")
write(template.replace("__AUTH_PROXY_CIDR__", selected))
print("Prepared central-auth Grafana configuration for its isolated gateway network. No services started.")
