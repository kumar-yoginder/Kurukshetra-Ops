#!/usr/bin/env python3
"""No-network failure and path-integrity checks for speed telemetry."""
from datetime import datetime, timezone
import unittest
from unittest.mock import patch
from pydantic import ValidationError
from network_speed import InternetProbe, SpeedReport, SpeedSample

class SpeedTests(unittest.TestCase):
    def test_truncated_download_does_not_publish_a_speed(self):
        probe = InternetProbe()
        with patch.object(probe, "request", side_effect=[(b"", .1)] * 3 + [(b"short", .1)]) as request:
            sample = probe.run()
        self.assertEqual(sample.test_state, "partial")
        self.assertIsNone(sample.download_mbps)
        self.assertIsNone(sample.upload_mbps)
        self.assertEqual(request.call_count, 4)

    def test_upload_failure_preserves_only_completed_measurements(self):
        probe = InternetProbe()
        with patch.object(probe, "request", side_effect=[(b"", .1)] * 3 + [(b"x" * probe.download_bytes, 1), OSError("unavailable")]):
            sample = probe.run()
        self.assertEqual(sample.test_state, "partial")
        self.assertGreater(sample.download_mbps, 0)
        self.assertIsNone(sample.upload_mbps)

    def test_connection_failure_is_not_reported_as_zero(self):
        with patch.object(InternetProbe, "request", side_effect=OSError("unavailable")):
            sample = InternetProbe().run()
        self.assertEqual(sample.test_state, "unavailable")
        self.assertIsNone(sample.download_mbps)
        self.assertIsNone(sample.upload_mbps)

    def test_nonfinite_speed_is_rejected(self):
        with self.assertRaises(ValidationError):
            SpeedSample(checked=datetime.now(timezone.utc), download_bytes=0, upload_bytes=0, download_mbps=float("nan"))

    def test_unverified_tor_speed_is_rejected(self):
        now = datetime.now(timezone.utc)
        internet = SpeedSample(checked=now, download_bytes=0, upload_bytes=0)
        tor = SpeedSample(checked=now, download_bytes=0, upload_bytes=0, verified_tor=False, download_mbps=10)
        with self.assertRaises(ValidationError):
            SpeedReport(updated=now, internet=internet, tor=tor)

if __name__ == "__main__":
    unittest.main()
