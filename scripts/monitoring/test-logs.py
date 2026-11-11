"""Privacy and resource-boundary regression checks for log summaries."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
spec=importlib.util.spec_from_file_location('log_collector',Path(__file__).with_name('collect-logs.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class LogTests(unittest.TestCase):
    def test_private_messages_never_exported(self):
        private='123456:SECRET_TOKEN user_id=987654321 Alice 192.168.1.9 https://api.telegram.org/botSECRET/'
        for prefix in ('ERROR timeout','WARNING connection refused','INFO started','CRITICAL unauthorized'):
            event=module.classify('2026-11-11T12:00:00.123456789Z '+prefix+' '+private,'chitragupt')
            output=event.model_dump_json();self.assertNotIn('SECRET',output);self.assertNotIn('Alice',output);self.assertNotIn('987654321',output);self.assertNotIn('192.168',output)
    def test_unclassified_and_invalid_timestamp_omitted(self):
        self.assertIsNone(module.classify('2026-11-11T12:00:00Z some private message','gateway'))
        self.assertIsNone(module.classify('not-a-time ERROR token','gateway'))
        self.assertIsNone(module.classify('2026-11-11T12:00:00 ERROR secret','gateway'))
    def test_output_rejects_unknown_labels_and_extra_fields(self):
        with self.assertRaises(ValueError):module.Event(timestamp=datetime.now(timezone.utc),service='arbitrary_user',level='info',kind='informational')
        with self.assertRaises(ValueError):module.Event(timestamp=datetime.now(timezone.utc),service='gateway',level='info',kind='informational',message='secret')
    def test_bounded_process_output(self):
        data,code,bounded=module.bounded_read([sys.executable,'-c',"print('x'*100000)"],cap=1024)
        self.assertTrue(bounded);self.assertLessEqual(len(data),1024)
    def test_timeout(self):
        data,code,bounded=module.bounded_read([sys.executable,'-c','import time;time.sleep(5)'],seconds=0.1)
        self.assertTrue(bounded);self.assertNotEqual(code,0)
    def test_retention_and_deduplication(self):
        now=datetime.now(timezone.utc)
        def event(stamp):return module.Event(timestamp=stamp,service="gateway",level="info",kind="informational")
        recent=event(now)
        self.assertEqual(module.retained([recent,recent,event(now-timedelta(days=2)),event(now+timedelta(hours=1))],now),[recent])
        many=[event(now-timedelta(seconds=i)) for i in range(2200)]
        self.assertEqual(len(module.retained(many,now)),2000)
        self.assertEqual(module.retained(many,now)[-1].timestamp,now)
    def test_snapshot_limit(self):
        event=module.Event(timestamp=datetime.now(timezone.utc),service='gateway',level='info',kind='informational')
        with self.assertRaises(ValueError):module.Snapshot(updated=datetime.now(timezone.utc),events=[event]*2001,sources=[])
if __name__=='__main__':unittest.main()
