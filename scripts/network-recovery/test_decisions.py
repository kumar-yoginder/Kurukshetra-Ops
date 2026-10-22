import unittest
from ethernet_wifi_recovery import Decision

class Decisions(unittest.TestCase):
    def test_debounce_outage(self):
        d = Decision(3, 4)
        self.assertIsNone(d.sample(False, False))
        self.assertIsNone(d.sample(False, False))
        self.assertEqual(d.sample(False, False), 'up')
        for _ in range(100):
            self.assertIsNone(d.sample(False, True))

    def test_recovery_hysteresis(self):
        d = Decision(3, 4)
        for _ in range(3):
            self.assertIsNone(d.sample(True, True))
        self.assertEqual(d.sample(True, True), 'down')

    def test_intermittent_failure(self):
        d = Decision(3, 4)
        for _ in range(100):
            self.assertIsNone(d.sample(False, False))
            self.assertIsNone(d.sample(True, False))

    def test_recovery_interrupted(self):
        d = Decision(3, 4)
        for _ in range(3):
            self.assertIsNone(d.sample(True, True))
        self.assertIsNone(d.sample(False, True))
        self.assertIsNone(d.sample(True, True))


class PolicyRouting(unittest.TestCase):
    def test_wifi_lan_reply_route_and_renewal(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from types import SimpleNamespace
        import json
        import ethernet_wifi_recovery as m
        calls = []
        current_address = ['192.0.2.22']
        rules = []
        def fake(args):
            calls.append(args)
            output = ''
            if args[:5] == ['ip', '-j', '-4', 'rule', 'show']:
                output = json.dumps(rules)
            elif args[:5] == ['ip', '-j', '-4', 'addr', 'show']:
                output = json.dumps([{'addr_info': [{'family':'inet', 'scope':'global',
                    'local':current_address[0], 'prefixlen':24}]}])
            elif 'show' in args:
                output = '[]'
            elif args[2:4] == ['rule', 'add']:
                rules[:] = [{'priority':10421, 'table':10421, 'src':current_address[0]}]
            elif args[2:4] == ['rule', 'del']:
                rules.clear()
            return SimpleNamespace(returncode=0, stdout=output)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(m.WifiPolicy, 'STATE', Path(directory)/'state'), patch.object(m, 'command', fake):
                policy = m.WifiPolicy('wlan0')
                self.assertTrue(policy.sync())
                self.assertIn(['ip','-4','route','replace','table','10421','192.0.2.0/24','dev','wlan0','src','192.0.2.22'], calls)
                self.assertFalse(any('default' in c for c in calls))
                current_address[0] = '192.0.2.23'
                policy.sync()
                self.assertIn(['ip','-4','rule','del','priority','10421','from','192.0.2.22/32','lookup','10421'], calls)
                self.assertEqual(policy.previous['address'], '192.0.2.23')

    def test_missing_table_partial_json_is_empty(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from types import SimpleNamespace
        import ethernet_wifi_recovery as m
        def fake(args):
            if 'route' in args:
                return SimpleNamespace(returncode=2, stdout='[', stderr='Error: ipv4: FIB table does not exist.\nDump terminated\n')
            return SimpleNamespace(returncode=0, stdout='[]', stderr='')
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(m.WifiPolicy, 'STATE', Path(directory)/'state'), patch.object(m, 'command', fake):
                self.assertIsNone(m.WifiPolicy('wlan0').previous)

    def test_other_route_query_failure_is_rejected(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from types import SimpleNamespace
        import ethernet_wifi_recovery as m
        def fake(args):
            if 'route' in args:
                return SimpleNamespace(returncode=2, stdout='[', stderr='permission denied')
            return SimpleNamespace(returncode=0, stdout='[]', stderr='')
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(m.WifiPolicy, 'STATE', Path(directory)/'state'), patch.object(m, 'command', fake):
                with self.assertRaisesRegex(RuntimeError, 'cannot inspect reserved'):
                    m.WifiPolicy('wlan0')

    def test_occupied_priority_rejected(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from types import SimpleNamespace
        import ethernet_wifi_recovery as m
        def fake(args):
            return SimpleNamespace(returncode=0, stdout='[{"priority":10421,"table":999}]' if 'rule' in args else '[]')
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(m.WifiPolicy, 'STATE', Path(directory)/'state'), patch.object(m, 'command', fake):
                with self.assertRaises(RuntimeError):
                    m.WifiPolicy('wlan0')

if __name__ == '__main__':
    unittest.main()
