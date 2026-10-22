"""Source-only tests: temporary files and mocked network commands; no root required."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]

class SourceTests(unittest.TestCase):
    def test_address_range(self):
        source = (SOURCE / 'trial.sh').read_text()
        validation = source.split('[[ $CLIENT_TUNNEL_IP =~', 1)[1].split('[[ -s $1/wg.conf ]]', 1)[0]
        validation = '[[ $CLIENT_TUNNEL_IP =~' + validation
        for value, valid in [('10.77.0.2', True), ('10.77.0.254', True),
                             ('10.77.0.1', False), ('10.77.0.255', False),
                             ('10.77.0.02', False), ('10.78.0.2', False),
                             ('10.77.0.2/32', False), ('10.77.0.999', False)]:
            result = subprocess.run(['bash', '-c', 'set -e; CLIENT_TUNNEL_IP=$1; ' + validation,
                                     'test', value], capture_output=True)
            self.assertEqual(result.returncode == 0, valid, value)

    def test_rollback_generation_guard(self):
        source = (SOURCE / 'trial.sh').read_text()
        rollback = source.split("<<'ROLLBACK'\n", 1)[1].split('\nROLLBACK', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / 'old'; old.mkdir()
            new = root / 'new'; new.mkdir()
            state = root / 'session'
            log = root / 'calls'
            commands = root / 'bin'; commands.mkdir()
            for command in ['flock', 'resolvectl', 'ip', 'nft', 'systemctl']:
                mock = commands / command
                mock.write_text('#!/bin/sh\nprintf "%s\\n" "' + command + ' $*" >> "$MOCK_LOG"\n')
                mock.chmod(0o755)
            transformed = rollback.replace('/run/kurukshetra-tor.lock', str(root / 'lock')).replace('/run/kurukshetra-tor-session', str(state))
            script = old / 'rollback.sh'; script.write_text(transformed)
            env = dict(os.environ, PATH=str(commands) + ':' + os.environ['PATH'], MOCK_LOG=str(log))
            state.write_text(str(new) + '\ntor-client-trial-2\n')
            subprocess.run(['bash', str(script)], env=env, check=True, capture_output=True)
            self.assertEqual(state.read_text(), str(new) + '\ntor-client-trial-2\n')
            self.assertNotIn('ip ', log.read_text())
            log.write_text('')
            state.write_text(str(old) + '\ntor-client-trial-1\nconfirmed\n')
            subprocess.run(['bash', str(script), '--timer'], env=env, check=True, capture_output=True)
            self.assertTrue(state.exists())
            self.assertNotIn('ip ', log.read_text())
            log.write_text('')
            state.write_text(str(old) + '\ntor-client-trial-1\n')
            subprocess.run(['bash', str(script)], env=env, check=True, capture_output=True)
            self.assertFalse(state.exists())
            self.assertIn('ip link delete torwg0', log.read_text())
            self.assertIn('systemctl stop tor-client-trial-1.timer', log.read_text())

    def test_shell_syntax(self):
        for filename in ['trial.sh', 'tor-client.sh']:
            subprocess.run(['bash', '-n', str(SOURCE / filename)], check=True)

if __name__ == '__main__':
    unittest.main()
