#!/usr/bin/env python3
"""Publish Chitragupt runtime and registry aggregates; never calls Telegram."""
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Literal
ROOT = Path(__file__).resolve().parents[2]
try:
    import pydantic
except ImportError:
    interpreter = ROOT / ".venv-router/bin/python"
    os.execv(str(interpreter), [str(interpreter), __file__])
from pydantic import BaseModel, ConfigDict, Field
from chitragupt_models import RegistrySummary

class RuntimeState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["created", "running", "paused", "restarting", "removing", "exited", "dead", "unknown", "missing"] = "unknown"
    uptime_seconds: int | None = Field(default=None, ge=0)
    restarts: int | None = Field(default=None, ge=0)

class BotSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    updated: datetime
    state: Literal["available", "partial", "unavailable"] = "unavailable"
    runtime: RuntimeState = Field(default_factory=RuntimeState)
    registry: RegistrySummary | None = None
    application_health: Literal["not_instrumented"] = "not_instrumented"

snapshot = BotSnapshot(updated=datetime.now(timezone.utc))
try:
    runtime = subprocess.run(["docker", "inspect", "--format", "{{.State.Status}}|{{.State.StartedAt}}|{{.RestartCount}}", "chitragupt_bot"], capture_output=True, text=True, timeout=5, check=True)
    state, started, restarts = runtime.stdout.strip().split("|")
    elapsed = max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds())) if state == "running" else None
    snapshot.runtime = RuntimeState(state=state, uptime_seconds=elapsed, restarts=int(restarts))
    if state == "running":
        probe = subprocess.run(["docker", "exec", "-i", "--user", "chitragupt_user", "chitragupt_bot", "python", "-"], input=(ROOT / "scripts/monitoring/chitragupt_probe.py").read_text(), capture_output=True, text=True, timeout=8, check=True)
        snapshot.registry = RegistrySummary.model_validate_json(probe.stdout)
        snapshot.state = "available" if snapshot.registry.chats_state == snapshot.registry.rules_state == "available" else "partial"
    else:
        snapshot.state = "partial"
except (OSError, ValueError, subprocess.SubprocessError):
    pass
path = ROOT / "config/nginx/www"
fd, temporary = tempfile.mkstemp(prefix=".chitragupt-", dir=path)
try:
    with os.fdopen(fd, "w") as output:
        os.fchmod(output.fileno(), 0o644)
        output.write(snapshot.model_dump_json(indent=2) + "\n")
    os.replace(temporary, path / "chitragupt.json")
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
