"""Ownership guards mocked only: these tests never call real systemctl."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

COMMON = Path(__file__).with_name('persistent-common.sh')

class Guards(unittest.TestCase):
    def invoke(self, unit_text, fragment='', timer_fragment='', symlink=False, timer=False):
        with tempfile.TemporaryDirectory() as directory:
            unit = Path(directory)/'unit'
            unit.write_text(unit_text)
            if symlink:
                other = Path(directory)/'link'
                other.symlink_to(unit)
                unit = other
            env = dict(os.environ, COMMON=str(COMMON), UNIT=str(unit), FRAGMENT=fragment,
                       TIMER_FRAGMENT=timer_fragment)
            script = '''
. "$COMMON"
unit_file=$UNIT
systemctl() {
    case "$1" in
        show)
            case "$2" in
                *rollback*) printf '%s\\n' "$TIMER_FRAGMENT";;
                *) printf '%s\\n' "$FRAGMENT";;
            esac;;
        *) echo UNEXPECTED_MUTATION; return 91;;
    esac
}
'''
            script += 'stop_owned_trial_timer\n' if timer else 'check_unit_ownership\n'
            return subprocess.run(['sh', '-c', script], env=env, capture_output=True, text=True)

    def test_unrelated_unit_refused(self):
        self.assertNotEqual(self.invoke('# other project\n').returncode, 0)

    def test_owned_unit_accepted(self):
        self.assertEqual(self.invoke('# Managed by Kurukshetra-Ops network-recovery v1\n').returncode, 0)

    def test_symlink_refused(self):
        self.assertNotEqual(self.invoke('# Managed by Kurukshetra-Ops network-recovery v1\n', symlink=True).returncode, 0)

    def test_unrelated_loaded_unit_refused(self):
        self.assertNotEqual(self.invoke('# Managed by Kurukshetra-Ops network-recovery v1\n', fragment='/vendor/other.service').returncode, 0)

    def test_unrelated_timer_not_stopped(self):
        result = self.invoke('', timer_fragment='/etc/systemd/system/unrelated.timer', timer=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('UNEXPECTED_MUTATION', result.stdout)


class DynamicRollback(unittest.TestCase):
    def test_dynamic_timer_stopped_before_any_service(self):
        env = dict(os.environ, COMMON=str(COMMON))
        script = r'''
. "$COMMON"
systemctl() {
    case "$1" in
        list-units) echo 'kurukshetra-network-test-rollback-123.timer loaded active waiting';;
        show)
            case "$4" in
                FragmentPath)
                    case "$2" in
                        *test-rollback-123*) echo "/run/systemd/transient/$2";;
                    esac;;
                Unit) echo kurukshetra-network-test-rollback-123.service;;
                ExecStart) echo '{ path=/usr/local/sbin/kurukshetra-network-recovery-rollback ; argv[]=/usr/local/sbin/kurukshetra-network-recovery-rollback ; ignore_errors=no ; }';;
            esac;;
        stop) echo "STOP $2";;
    esac
}
stop_owned_trial_timer
'''
        result = subprocess.run(['sh','-c',script], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.startswith('STOP ')]
        first_service = next(i for i,l in enumerate(lines) if l.endswith('.service'))
        self.assertTrue(all(l.endswith('.timer') for l in lines[:first_service]))
        self.assertIn('STOP kurukshetra-network-test-rollback-123.timer', lines)
        self.assertIn('STOP kurukshetra-network-test-rollback-123.service', lines)

if __name__ == '__main__':
    unittest.main()
