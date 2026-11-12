#!/usr/bin/python3
"""Tests for the relay's OpenRC unit and its installer. Run from the tangled tree: python3 test_honey_fca_egress.py

The unit is exercised without starting anything: its start_pre runs in a harness shell with stubbed identity and
OpenRC helpers (every refusal path), and the installer runs against a scratch PREFIX. The root-owned checks need
passwordless sudo; without it those tests are SKIPPED by name, never passed."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
BODY = os.path.join(HERE, 'honey-fca-egress')
INSTALL = os.path.join(HERE, 'honey-fca-egress-install')
RELAY = os.path.join(LANE, 'egress', 'fca_egress_relay.py')
EGRESS_MD = os.path.join(LANE, 'egress', 'EGRESS.md')


def read(path):
    with open(path) as f:
        return f.read()


def sudo_ok():
    return subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0


def sh(script, env=None, timeout=30):
    return subprocess.run(['sh', '-c', script], capture_output=True, text=True, timeout=timeout, env=env)


def sha(path):
    return subprocess.run(['sha256sum', path], capture_output=True, text=True, check=True).stdout.split()[0]


def need_sudo(test):
    def wrapper(self):
        if not sudo_ok():
            self.skipTest('SKIPPED %s: passwordless sudo is needed to make root-owned fixtures' % test.__name__)
        return test(self)
    wrapper.__name__ = test.__name__
    return wrapper


class UnitBody(unittest.TestCase):
    def test_body_parses_in_sh_and_bash(self):
        for shell in ('sh', 'bash'):
            r = subprocess.run([shell, '-n', BODY], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, (shell, r.stderr))

    def test_the_unit_runs_exactly_the_relay_as_the_unprivileged_identity(self):
        r = sh('. "%s"; printf "%%s\\n" "$command" "$command_args" "$command_user" "$command_background" "$pidfile" "$run_dir"' % BODY)
        self.assertEqual(r.returncode, 0, r.stderr)
        command, args, user, background, pidfile, run_dir = r.stdout.splitlines()
        self.assertEqual(command, '/usr/bin/python3')
        self.assertEqual(args, '-I /opt/honey-fca-dsh/egress/fca_egress_relay.py')  # isolated mode, the relay, and NO other argument
        self.assertEqual(user, 'fca-egress:fca-egress')
        self.assertEqual(background, 'true')
        self.assertEqual(pidfile, '/run/honey-fca-egress.pid')
        self.assertEqual(run_dir, '/run/fca-dsh-egress')
        self.assertFalse(re.search(r'command_user="?root', read(BODY)))

    def test_the_unit_names_nothing_the_relay_must_not_read(self):
        text = read(BODY)
        for forbidden in ('/home/gille', 'agent-deepseek/', 'cortex', 'env_file', 'export '):
            self.assertNotIn(forbidden, text)

    def test_egress_md_documents_the_unit_and_installer(self):
        text = read(EGRESS_MD)
        for name in ('honey-fca-egress', 'honey-fca-egress-install', '--expect-relay-sha256', 'S04honey-fca-egress'):
            self.assertIn(name, text)


HARNESS = r'''
eerror() { echo "E: $*" >&2; }
einfo() { :; }
checkpath() { echo "checkpath $*" >> "$LOG"; }
setfacl() { echo "setfacl $*" >> "$LOG"; }
id() {
    case "$1:$2" in
        -u:fca-egress) [ "$T_NO_IDENTITY" = 1 ] && return 1; echo "${T_RELAY_UID:-985}" ;;
        -G:fca-egress) echo "${T_RELAY_GROUPS:-985}" ;;
        -g:fca-egress) echo 985 ;;
        -u:agent-deepseek) echo "${T_WORKER_UID:-2012}" ;;
        *) command id "$@" ;;
    esac
}
relay_root="$T_ROOT"
. "$BODY"
relay_root="$T_ROOT"
start_pre
echo "rc=$?"
'''


class StartPre(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='fca-unit-')
        self.log = os.path.join(self.tmp, 'calls.log')
        with open(self.log, 'w'):
            pass
        self.root = os.path.join(self.tmp, 'egress')

    def tearDown(self):
        subprocess.run(['sudo', '-n', 'rm', '-rf', self.tmp], capture_output=True)

    def make_root(self, root_owned=True, mode='0755', relay=True):
        os.makedirs(self.root)
        if relay:
            with open(os.path.join(self.root, 'fca_egress_relay.py'), 'w') as f:
                f.write('# fixture\n')
        if root_owned:
            subprocess.run(['sudo', '-n', 'chown', '-R', 'root:root', self.root], check=True)
        subprocess.run(['sudo', '-n', 'chmod', '-R', mode if mode else '0755', self.root], check=True)

    def run_pre(self, **env_extra):
        env = dict(os.environ, LOG=self.log, BODY=BODY, T_ROOT=self.root, **env_extra)
        r = sh(HARNESS, env=env)
        calls = read(self.log).splitlines()
        return r.stdout.strip().splitlines()[-1], r.stderr.strip(), calls

    @need_sudo
    def test_a_good_environment_creates_the_socket_dir_and_acl_and_nothing_else(self):
        self.make_root()
        rc, err, calls = self.run_pre()
        self.assertEqual(rc, 'rc=0', err)
        self.assertEqual(calls, ['checkpath -d -m 0700 -o fca-egress:fca-egress /run/fca-dsh-egress',
                                 'setfacl -m u:2012:--x /run/fca-dsh-egress',
                                 'checkpath -f -m 0640 -o fca-egress:fca-egress /var/log/honey-fca-egress.log'])

    def test_missing_relay_identity_is_refused_before_anything_is_created(self):
        os.makedirs(self.root)
        rc, err, calls = self.run_pre(T_NO_IDENTITY='1')
        self.assertEqual(rc, 'rc=1')
        self.assertIn('no fca-egress identity', err)
        self.assertEqual(calls, [])

    def test_uid_zero_relay_identity_is_refused(self):
        os.makedirs(self.root)
        rc, err, calls = self.run_pre(T_RELAY_UID='0')
        self.assertEqual((rc, calls), ('rc=1', []))
        self.assertIn('uid 0', err)

    def test_a_relay_identity_with_supplementary_groups_is_refused(self):
        os.makedirs(self.root)
        rc, err, calls = self.run_pre(T_RELAY_GROUPS='985 2000')
        self.assertEqual((rc, calls), ('rc=1', []))
        self.assertIn('supplementary groups', err)

    def test_a_worker_that_is_not_uid_2012_is_refused(self):
        os.makedirs(self.root)
        rc, err, calls = self.run_pre(T_WORKER_UID='2013')
        self.assertEqual((rc, calls), ('rc=1', []))
        self.assertIn('not uid 2012', err)

    def test_a_missing_relay_file_is_refused(self):
        os.makedirs(self.root)
        rc, err, calls = self.run_pre()
        self.assertEqual((rc, calls), ('rc=1', []))
        self.assertIn('missing', err)

    def test_a_relay_directory_not_owned_by_root_is_refused(self):
        os.makedirs(self.root)
        with open(os.path.join(self.root, 'fca_egress_relay.py'), 'w') as f:
            f.write('# owned by the test user\n')
        rc, err, calls = self.run_pre()
        self.assertEqual((rc, calls), ('rc=1', []))
        self.assertIn('not root-owned and read-only', err)

    @need_sudo
    def test_a_group_writable_relay_file_is_refused_even_when_root_owned(self):
        self.make_root()
        subprocess.run(['sudo', '-n', 'chmod', 'g+w', os.path.join(self.root, 'fca_egress_relay.py')], check=True)
        rc, err, calls = self.run_pre()
        self.assertEqual((rc, calls), ('rc=1', []))
        self.assertIn('not root-owned and read-only', err)


class Installer(unittest.TestCase):
    def setUp(self):
        self.prefix = tempfile.mkdtemp(prefix='fca-prefix-')
        self.good = sha(RELAY)

    def tearDown(self):
        subprocess.run(['sudo', '-n', 'rm', '-rf', self.prefix], capture_output=True)

    def run_inst(self, *args, root=True, **env):
        env = dict(os.environ, HONEY_FCA_EGRESS_PREFIX=self.prefix, **env)
        cmd = ([ 'sudo', '-n', '--preserve-env=HONEY_FCA_EGRESS_PREFIX'] if root else []) + [INSTALL] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)

    def written(self):
        out = []
        for d, _, files in os.walk(self.prefix):
            out += [os.path.relpath(os.path.join(d, f), self.prefix) for f in files]
        return sorted(out)

    def test_install_without_the_expected_hash_is_refused_and_writes_nothing(self):
        r = self.run_inst('--dry-run', 'install', root=False)  # dry run continues but says a real run would refuse
        self.assertIn('--expect-relay-sha256 is required', r.stderr)
        self.assertEqual(self.written(), [])
        self.assertEqual(self.run_inst('install', root=False).returncode, 1)

    def test_a_wrong_hash_is_refused_and_writes_nothing(self):
        r = self.run_inst('--dry-run', '--expect-relay-sha256', '0' * 64, 'install', root=False)
        self.assertIn('relay hash mismatch', r.stderr)
        self.assertEqual(self.written(), [])

    def test_a_malformed_hash_is_refused(self):
        for bad in ('abc', 'G' * 64, self.good.upper()):
            r = self.run_inst('--dry-run', '--expect-relay-sha256', bad, 'install', root=False)
            self.assertIn('--expect-relay-sha256', r.stderr, bad)
            self.assertEqual(self.written(), [])

    def test_dry_run_with_the_right_hash_prints_the_plan_and_writes_nothing(self):
        r = self.run_inst('--dry-run', '--expect-relay-sha256', self.good, 'install', root=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('would: install -m 0644 -o root -g root', r.stdout)
        self.assertEqual(self.written(), [])

    @need_sudo
    def test_install_places_only_the_relay_and_the_unit_with_root_ownership(self):
        r = self.run_inst('--expect-relay-sha256', self.good, 'install')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.written(), ['etc/init.d/honey-fca-egress', 'opt/honey-fca-dsh/egress/fca_egress_relay.py'])
        for rel, mode in (('opt/honey-fca-dsh/egress/fca_egress_relay.py', '644'), ('etc/init.d/honey-fca-egress', '755'),
                          ('opt/honey-fca-dsh/egress', '755')):
            st = subprocess.run(['stat', '-c', '%a %U:%G', os.path.join(self.prefix, rel)], capture_output=True, text=True).stdout.split()
            self.assertEqual(st, [mode, 'root:root'], rel)
        self.assertEqual(sha(os.path.join(self.prefix, 'opt/honey-fca-dsh/egress/fca_egress_relay.py')), self.good)
        self.assertIn('not started and not enabled', r.stdout)

    @need_sudo
    def test_a_second_install_changes_nothing_and_a_drifted_file_is_backed_up(self):
        self.run_inst('--expect-relay-sha256', self.good, 'install')
        again = self.run_inst('--expect-relay-sha256', self.good, 'install')
        self.assertEqual(again.stdout.count('unchanged'), 2, again.stdout)
        target = os.path.join(self.prefix, 'etc/init.d/honey-fca-egress')
        subprocess.run(['sudo', '-n', 'sh', '-c', 'echo drift >> "%s"' % target], check=True)
        r = self.run_inst('--expect-relay-sha256', self.good, 'install')
        self.assertIn('installed %s' % target, r.stdout)
        self.assertEqual(len([f for f in self.written() if '.bak-' in f]), 1)

    @need_sudo
    def test_enable_creates_the_runlevel_link_and_disable_removes_it(self):
        self.run_inst('--expect-relay-sha256', self.good, 'install')
        status = self.run_inst('status', root=False).stdout
        self.assertIn('boot link  ABSENT', status)
        self.assertEqual(self.run_inst('enable').returncode, 0)
        link = os.path.join(self.prefix, 'etc/rc2.d/S04honey-fca-egress')
        self.assertEqual(os.readlink(link), '../init.d/honey-fca-egress')
        self.assertIn('boot link  present', self.run_inst('status', root=False).stdout)
        self.assertIn('already enabled', self.run_inst('enable').stdout)
        self.assertEqual(self.run_inst('disable').returncode, 0)
        self.assertFalse(os.path.lexists(link))

    def test_enable_refuses_when_the_unit_is_not_installed(self):
        if not sudo_ok():
            self.skipTest('SKIPPED: passwordless sudo is needed to run the installer as root')
        r = self.run_inst('enable')
        self.assertEqual(r.returncode, 1)
        self.assertIn('is not installed', r.stderr)

    @need_sudo
    def test_status_reports_a_drifted_unit_as_different_from_this_tree(self):
        self.run_inst('--expect-relay-sha256', self.good, 'install')
        subprocess.run(['sudo', '-n', 'sh', '-c', 'echo drift >> "%s"' % os.path.join(self.prefix, 'opt/honey-fca-dsh/egress/fca_egress_relay.py')], check=True)
        self.assertIn('DIFFERS', self.run_inst('status', root=False).stdout)

    def test_the_installer_never_starts_or_stops_anything(self):
        text = re.sub(r"cat <<'USAGE'.*?\nUSAGE\n", '', read(INSTALL), flags=re.S)  # the usage and echo text may NAME commands
        called = re.findall(r'^\s*(?:run\s+)?(rc-service|rc-update|service|start-stop-daemon|kill|pkill|systemctl)\b', text, flags=re.M)
        self.assertEqual(called, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
