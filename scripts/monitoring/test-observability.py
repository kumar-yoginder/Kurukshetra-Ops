#!/usr/bin/env python3
"""Offline metric allowlist and privacy-boundary tests."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pydantic import ValidationError

path = Path(__file__).with_name("collect-observability.py")
spec = importlib.util.spec_from_file_location("observability_exporter", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

class MetricPrivacyTests(unittest.TestCase):
    def test_unknown_metric_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            module.Metric(name="private_user_name", value=1)
    def test_identity_label_is_rejected(self):
        with self.assertRaises(ValidationError):
            module.Metric(name="kurukshetra_service_running", value=1, labels={"user_id": "123456789"})
    def test_unapproved_service_label_is_rejected(self):
        with self.assertRaises(ValidationError):
            module.Metric(name="kurukshetra_service_running", value=1, labels={"service": "PRIVATE_PERSON"})
    def test_nonfinite_or_negative_value_is_rejected(self):
        for value in (float("nan"), float("inf"), -1):
            with self.assertRaises(ValidationError):
                module.Metric(name="kurukshetra_host_load", value=value)
    def test_extra_snapshot_fields_never_become_labels(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "config/nginx/www"
            target.mkdir(parents=True)
            now = datetime.now(timezone.utc).isoformat()
            values = {
                "status.json": {"services": [{"name": "PRIVATE_PERSON", "state": "running"}, {"name": "Chitragupt", "state": "running"}]},
                "chitragupt.json": {"updated": now, "user_id": "123456789", "token": "PRIVATE_TOKEN", "runtime": {"uptime_seconds": 10, "restarts": 0}, "registry": {"user_identities": 2, "managed_chats": 1, "chat_identities": 1, "role_definitions": 5, "names": ["PRIVATE_PERSON"], "role_counts": [{"level": 10, "count": 2}]}},
                "speed-metrics.json": {"internet": {"checked": now, "download_mbps": 10, "upload_mbps": 2, "response_ms": 100, "private_exit_address": "PRIVATE_ADDRESS"}},
            }
            for name, value in values.items():
                (target / name).write_text(json.dumps(value, indent=2) + "\n")
            fake = subprocess.CompletedProcess([], 0, stdout="chitragupt_bot|1.00%|32MiB / 512MiB\nPRIVATE_PERSON|2.0%|1MiB / 5MiB\n", stderr="")
            with patch.object(module, "ROOT", root), patch.object(module.subprocess, "run", return_value=fake):
                output = module.SnapshotExporter().collect()
            for private in ("PRIVATE_PERSON", "PRIVATE_TOKEN", "PRIVATE_ADDRESS", "123456789", "user_id"):
                self.assertNotIn(private, output)
            self.assertIn('service="chitragupt"', output)

if __name__ == "__main__":
    unittest.main()
