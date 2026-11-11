#!/usr/bin/env python3
"""Publish an allowlisted, low-cardinality Prometheus snapshot; never reads bot secrets/logs."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Literal
ROOT = Path(__file__).resolve().parents[2]
try:
    import pydantic
except ImportError:
    python = ROOT / ".venv-router/bin/python"
    os.execv(str(python), [str(python), __file__])
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Metric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Literal["kurukshetra_host_memory_bytes", "kurukshetra_host_load", "kurukshetra_host_cpu_cores", "kurukshetra_host_cpu_seconds_total", "kurukshetra_host_filesystem_bytes", "kurukshetra_service_running", "kurukshetra_service_health_known", "kurukshetra_service_healthy", "kurukshetra_container_cpu_percent", "kurukshetra_container_memory_bytes", "kurukshetra_docker_stats_available", "kurukshetra_snapshot_fresh", "chitragupt_container_uptime_seconds", "chitragupt_container_restarts_total", "chitragupt_registry_entries", "chitragupt_role_users", "kurukshetra_connection_mbps", "kurukshetra_connection_response_milliseconds", "kurukshetra_collector_last_run_unixtime"]
    value: float = Field(ge=0, allow_inf_nan=False)
    labels: dict[Literal["service", "kind", "mode", "window", "signal", "level"], str] = Field(default_factory=dict)
    @field_validator("labels")
    @classmethod
    def bounded_labels(cls, labels):
        allowed = {
            "service": set(SERVICES.values()),
            "kind": {"total", "available", "users", "managed_chats", "chat_identities", "roles", "download", "upload"},
            "mode": {"user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal"},
            "window": {"1m", "5m", "15m"},
            "signal": {"chitragupt", "home", "tor"},
        }
        for key, value in labels.items():
            if key == "level":
                if not re.fullmatch(r"[0-9]{1,6}", value) or int(value) > 100000:
                    raise ValueError("invalid role level")
            elif value not in allowed[key]:
                raise ValueError("unapproved metric label")
        return labels
    def line(self):
        tags = ",".join(key + "=" + json.dumps(value) for key, value in sorted(self.labels.items()))
        return self.name + ("{" + tags + "}" if tags else "") + " " + str(self.value)

SERVICES = {
    "pihole": "pihole", "kurukshetra-gateway": "gateway", "chitragupt_bot": "chitragupt",
    "kurukshetra-ops-identity-1": "identity", "kurukshetra-ops-gateway-waf-1": "waf",
    "kurukshetra-ops-web-router-1": "router", "kurukshetra-ops-pihole-bridge-1": "bridge",
    "kurukshetra-ops-router-inventory-1": "inventory", "kurukshetra-ops-tor-gateway-1": "tor",
    "kurukshetra-ops-grafana-1": "grafana", "kurukshetra-ops-prometheus-1": "prometheus",
    "kurukshetra-ops-alloy-1": "alloy",
}
DISPLAY = {"Pi-hole": "pihole", "HTTPS gateway": "gateway", "Chitragupt": "chitragupt", "Bot": "chitragupt", "Central identity": "identity", "Web application firewall": "waf", "Application router": "router", "Pi-hole session bridge": "bridge", "Private inventory": "inventory", "Tor gateway": "tor", "Grafana": "grafana", "Prometheus": "prometheus", "Grafana Alloy": "alloy"}

def read(name):
    try:
        return json.loads((ROOT / "config/nginx/www" / name).read_text())
    except (OSError, ValueError):
        return {}

def mib_bytes(text):
    match = re.fullmatch(r"([0-9.]+)(B|kB|KB|KiB|MB|MiB|GB|GiB)", text.strip())
    if not match:
        raise ValueError("invalid memory amount")
    scale = {"B": 1, "kB": 1000, "KB": 1000, "KiB": 1024, "MB": 1000000, "MiB": 1048576, "GB": 1000000000, "GiB": 1073741824}
    return float(match[1]) * scale[match[2]]

class SnapshotExporter:
    def __init__(self):
        self.metrics = []
    def emit(self, name, value, **labels):
        if value is None:
            return
        try:
            self.metrics.append(Metric(name=name, value=float(value), labels=labels))
        except (ValueError, TypeError):
            pass
    def collect(self):
        now = datetime.now(timezone.utc)
        memory = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            if key in ("MemTotal", "MemAvailable"):
                memory[key] = int(value.strip().split()[0]) * 1024
        self.emit("kurukshetra_host_memory_bytes", memory.get("MemTotal"), kind="total")
        self.emit("kurukshetra_host_memory_bytes", memory.get("MemAvailable"), kind="available")
        for window, load in zip(("1m", "5m", "15m"), os.getloadavg()):
            self.emit("kurukshetra_host_load", load, window=window)
        self.emit("kurukshetra_host_cpu_cores", os.cpu_count())
        cpu = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        for mode, ticks in zip(("user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal"), cpu):
            self.emit("kurukshetra_host_cpu_seconds_total", int(ticks) / os.sysconf("SC_CLK_TCK"), mode=mode)
        fs = os.statvfs(ROOT)
        self.emit("kurukshetra_host_filesystem_bytes", fs.f_blocks * fs.f_frsize, kind="total")
        self.emit("kurukshetra_host_filesystem_bytes", fs.f_bavail * fs.f_frsize, kind="available")
        for service in read("status.json").get("services", []):
            name = DISPLAY.get(service.get("name"))
            if name:
                state = service.get("state")
                self.emit("kurukshetra_service_running", state in ("running", "healthy", "unhealthy", "starting"), service=name)
                self.emit("kurukshetra_service_health_known", state in ("healthy", "unhealthy", "starting"), service=name)
                if state in ("healthy", "unhealthy", "starting"):
                    self.emit("kurukshetra_service_healthy", state == "healthy", service=name)
        try:
            stats = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}", *SERVICES], capture_output=True, text=True, timeout=10)
            for line in stats.stdout.splitlines():
                name, cpu, memory = line.split("|", 2)
                if name in SERVICES:
                    self.emit("kurukshetra_container_cpu_percent", float(cpu.rstrip("%")), service=SERVICES[name])
                    self.emit("kurukshetra_container_memory_bytes", mib_bytes(memory.split("/", 1)[0]), service=SERVICES[name])
            self.emit("kurukshetra_docker_stats_available", 1)
        except (OSError, ValueError, subprocess.SubprocessError):
            self.emit("kurukshetra_docker_stats_available", 0)
        bot = read("chitragupt.json")
        try:
            age = (now - datetime.fromisoformat(bot["updated"].replace("Z", "+00:00"))).total_seconds()
            self.emit("kurukshetra_snapshot_fresh", -60 <= age < 180, signal="chitragupt")
            if -60 <= age < 180:
                self.emit("chitragupt_container_uptime_seconds", bot.get("runtime", {}).get("uptime_seconds"))
                self.emit("chitragupt_container_restarts_total", bot.get("runtime", {}).get("restarts"))
                registry = bot.get("registry") or {}
                for kind, field in (("users", "user_identities"), ("managed_chats", "managed_chats"), ("chat_identities", "chat_identities"), ("roles", "role_definitions")):
                    self.emit("chitragupt_registry_entries", registry.get(field), kind=kind)
                for role in registry.get("role_counts", []):
                    self.emit("chitragupt_role_users", role["count"], level=str(role["level"]))
        except (ValueError, KeyError, TypeError):
            self.emit("kurukshetra_snapshot_fresh", 0, signal="chitragupt")
        speed = read("speed-metrics.json")
        for key, signal in (("internet", "home"), ("tor", "tor")):
            sample = speed.get(key) or {}
            try:
                age = (now - datetime.fromisoformat(sample["checked"].replace("Z", "+00:00"))).total_seconds()
                fresh = -60 <= age < 1200 and (key != "tor" or sample.get("verified_tor") is True)
                self.emit("kurukshetra_snapshot_fresh", fresh, signal=signal)
                if fresh:
                    for kind in ("download", "upload"):
                        self.emit("kurukshetra_connection_mbps", sample.get(kind + "_mbps"), signal=signal, kind=kind)
                    self.emit("kurukshetra_connection_response_milliseconds", sample.get("response_ms"), signal=signal)
            except (ValueError, KeyError, TypeError):
                self.emit("kurukshetra_snapshot_fresh", 0, signal=signal)
        self.emit("kurukshetra_collector_last_run_unixtime", now.timestamp())
        return "\n".join(metric.line() for metric in self.metrics) + "\n"

if __name__ == "__main__":
    data = SnapshotExporter().collect()
    directory = ROOT / "config/nginx/www"
    fd, temporary = tempfile.mkstemp(prefix=".telemetry-", dir=directory)
    try:
        with os.fdopen(fd, "w") as output:
            os.fchmod(output.fileno(), 0o644)
            output.write(data)
        os.replace(temporary, directory / "telemetry.prom")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
