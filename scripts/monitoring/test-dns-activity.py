import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('collect-dns-activity.py'))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

class SummaryTests(unittest.TestCase):
    def test_window_internal_exclusion_and_redaction(self):
        now=200000
        rows=[('192.168.31.40',now-1,7),('192.168.31.40',now-3601,3),
              ('192.168.31.41',now-86400,2),('192.168.31.42',now-86401,999),
              ('172.19.0.1',now-1,999),('127.0.0.1',now-1,999)]
        result=collector.summarize(rows,now)
        self.assertEqual(result['queries'],12)
        self.assertEqual(result['client_count'],2)
        self.assertEqual(sum(result['hourly_queries']),12)
        self.assertEqual(result['clients'][0]['queries'],10)
        self.assertNotIn('192.168',str(result))
        self.assertNotIn('172.19',str(result))
        self.assertEqual(result['hourly_queries'][0],2)
        self.assertEqual(result['hourly_queries'][-1],7)
    def test_empty_is_available_zero(self):
        result=collector.summarize([],200000)
        self.assertEqual(result['client_count'],0)
        self.assertEqual(result['state'],'available')

if __name__=='__main__':unittest.main()
