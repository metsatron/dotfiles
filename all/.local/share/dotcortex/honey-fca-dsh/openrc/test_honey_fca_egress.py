#!/usr/bin/python3
"""Tests for the relay's OpenRC unit and its installer. Run from the tangled tree: python3 test_honey_fca_egress.py

The unit is exercised without starting anything: its start_pre runs in a harness shell with stubbed identity and
OpenRC helpers (every refusal path), and the installer runs against a scratch PREFIX. The root-owned checks need
passwordless sudo; without it those tests are SKIPPED by name, never passed.

The RealOpenRC class runs the unit under the real openrc-run and is GATED: it FAILS, naming the hazard, unless HONEY_DISPOSABLE_OPENRC_HOST
carries the exact statement in DISPOSABLE_VALUE, and it fails even then on a host with production init scripts (see rehearsal_gate). On a host
with no openrc-run it is a named skip. Do not run it on Honey: it is followed by OpenRC-managed python3 services crashing there (2026-11-12)."""
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
        for name in ('honey-fca-egress', 'honey-fca-egress-install', '--expect-relay-sha256', 'S04honey-fca-egress', 'start_post', 'command_user'):
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


OPENRC_RUN = '/sbin/openrc-run'
RC_BIN = '/lib/rc/bin'

# The RealOpenRC tests run the unit under the REAL openrc-run. On 2026-11-12 they were followed, on Honey, by OpenRC-managed python3
# services crashing (identity-proxy, which Aura's every chat depends on, and others; the mechanism is NOT confirmed). They therefore
# refuse to run unless the operator states that the host is disposable, and refuse even then if it carries production services.
# A refusal is a FAILURE on purpose: a skip that looks like a pass is how a hazard ships a second time.
DISPOSABLE_VAR = 'HONEY_DISPOSABLE_OPENRC_HOST'
DISPOSABLE_VALUE = 'yes-this-host-may-lose-every-python3-service'
PRODUCTION_MARKERS = ('/etc/init.d/identity-proxy', '/etc/init.d/gille-llama-swap', '/etc/init.d/hermes-gateway')


def rehearsal_gate(env, exists, sudo, identities):
    """('skip' | 'refuse' | 'run', message). Pure: no command is run here. Order matters: without openrc-run nothing can happen, so
    that is a named skip; with it, the operator's explicit statement comes before anything else."""
    if not exists(OPENRC_RUN):
        return 'skip', 'SKIPPED: there is no %s on this host; the RealOpenRC tests need a DISPOSABLE OpenRC host' % OPENRC_RUN
    if env.get(DISPOSABLE_VAR) != DISPOSABLE_VALUE:
        return 'refuse', ('REFUSED: the RealOpenRC tests run %s on THIS host, and on 2026-11-12 they were followed by OpenRC-managed python3 '
                          'services (identity-proxy and others) crashing on Honey. Run them only on a DISPOSABLE OpenRC host and say so with '
                          '%s=%s. This is a failure on purpose: a skip would look like a pass.' % (OPENRC_RUN, DISPOSABLE_VAR, DISPOSABLE_VALUE))
    marked = [m for m in PRODUCTION_MARKERS if exists(m)]
    if marked:
        return 'refuse', ('REFUSED: %s is set but this host carries production services (%s). The variable does not override that; '
                          'use a host that has none.' % (DISPOSABLE_VAR, ', '.join(marked)))
    if not (sudo() and identities()):
        return 'skip', 'SKIPPED: needs passwordless sudo and the fca-egress and agent-deepseek identities'
    return 'run', ''


def have_identities():
    return all(subprocess.run(['id', '-u', u], capture_output=True).returncode == 0 for u in ('fca-egress', 'agent-deepseek'))


class RealOpenRC(unittest.TestCase):
    """The unit under the real OpenRC. Rehearsals use a COPY with four path variables pointed at a scratch directory and a stand-in
    for the relay (a different service name), so nothing of the real service, /run/fca-dsh-egress or /etc/init.d is touched."""

    def setUp(self):
        verdict, why = rehearsal_gate(os.environ, os.path.exists, sudo_ok, have_identities)
        if verdict == 'skip':
            self.skipTest(why)
        if verdict == 'refuse':
            self.fail(why)
        self.tmp = tempfile.mkdtemp(prefix='fca-rehearsal-')
        subprocess.run(['sudo', '-n', 'chown', 'root:root', self.tmp], check=True)
        subprocess.run(['sudo', '-n', 'chmod', '0755', self.tmp], check=True)
        self.relay_dir = os.path.join(self.tmp, 'relay')
        self.run_dir = os.path.join(self.tmp, 'run')
        self.pidfile = os.path.join(self.tmp, 'unit.pid')
        self.unit = os.path.join(self.tmp, 'honey-fca-egress-rehearsal')
        subprocess.run(['sudo', '-n', 'install', '-d', '-m', '0755', '-o', 'root', '-g', 'root', self.relay_dir], check=True)
        text = read(BODY)
        for old, new in (('relay_root:=/opt/honey-fca-dsh/egress', 'relay_root:=%s' % self.relay_dir),
                         ('run_dir=/run/fca-dsh-egress', 'run_dir=%s' % self.run_dir),
                         ('log_file=/var/log/honey-fca-egress.log', 'log_file=%s/unit.log' % self.tmp),
                         ('pidfile="/run/honey-fca-egress.pid"', 'pidfile="%s"' % self.pidfile)):
            self.assertEqual(text.count(old), 1, old)
            text = text.replace(old, new)
        staged = os.path.join(tempfile.gettempdir(), os.path.basename(self.tmp) + '.unit')
        with open(staged, 'w') as f:
            f.write(text)
        subprocess.run(['sudo', '-n', 'install', '-m', '0755', '-o', 'root', '-g', 'root', staged, self.unit], check=True)
        os.unlink(staged)

    def tearDown(self):
        if not hasattr(self, 'tmp'):
            return
        subprocess.run(['sudo', '-n', OPENRC_RUN, self.unit, 'stop'], capture_output=True)
        if os.path.exists(self.pidfile):
            pid = read(self.pidfile).strip()
            subprocess.run(['sudo', '-n', 'kill', '-KILL', pid], capture_output=True)
        subprocess.run(['sudo', '-n', 'rm', '-rf', self.tmp], capture_output=True)

    def stand_in(self, binds):
        body = ('import socket, time\n'
                + ('s = socket.socket(socket.AF_UNIX)\ns.bind(%r)\n' % (self.run_dir + '/relay.sock') if binds else '')
                + 'time.sleep(60)\n')
        staged = os.path.join(tempfile.gettempdir(), os.path.basename(self.tmp) + '.relay')
        with open(staged, 'w') as f:
            f.write(body)
        subprocess.run(['sudo', '-n', 'install', '-m', '0644', '-o', 'root', '-g', 'root', staged,
                        os.path.join(self.relay_dir, 'fca_egress_relay.py')], check=True)
        os.unlink(staged)

    def dir_state(self):
        """The socket directory's ACL entries (owner rwx, the worker traverse-only, nothing for group or other) and its owner. stat's mode
        is not used: with a named ACL entry its group bits show the mask, so 0700 plus u:2012:--x reads as 710."""
        acl = subprocess.run(['sudo', '-n', 'getfacl', '-p', '-c', self.run_dir], capture_output=True, text=True).stdout.split()
        owner = subprocess.run(['sudo', '-n', 'stat', '-c', '%U:%G', self.run_dir], capture_output=True, text=True).stdout.strip()
        return sorted(acl), owner

    def rc(self, verb):
        return subprocess.run(['sudo', '-n', OPENRC_RUN, self.unit, verb], capture_output=True, text=True, timeout=90)

    def owner_of(self, pid):
        return subprocess.run(['ps', '-o', 'user=', '-p', pid], capture_output=True, text=True).stdout.strip()

    def test_openrc_accepts_the_real_unit_file(self):
        r = subprocess.run(['sudo', '-n', OPENRC_RUN, BODY, 'describe'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('fixed-upstream egress relay', r.stdout)
        r = subprocess.run(['sudo', '-n', OPENRC_RUN, BODY, 'status'], capture_output=True, text=True)
        self.assertIn(r.returncode, (0, 3), r.stdout + r.stderr)  # started or stopped, but parsed and answered
        self.assertIn('status:', r.stdout)

    def test_a_second_start_is_a_no_op_and_the_relay_never_runs_as_root(self):
        self.stand_in(binds=True)
        first = self.rc('start')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        pid = read(self.pidfile).strip()
        self.assertEqual(self.owner_of(pid), 'fca-egress')
        second = self.rc('start')
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn('already', second.stdout + second.stderr)
        self.assertEqual(read(self.pidfile).strip(), pid)
        self.assertEqual(self.dir_state(), (['group::---', 'mask::--x', 'other::---', 'user::rwx', 'user:agent-deepseek:--x'], 'fca-egress:fca-egress'))
        stopped = self.rc('stop')
        self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
        self.assertEqual(subprocess.run(['sudo', '-n', 'test', '-e', self.run_dir + '/relay.sock']).returncode, 1)  # the socket is gone
        self.assertEqual(subprocess.run(['sudo', '-n', 'test', '-f', self.relay_dir + '/fca_egress_relay.py']).returncode, 0)  # the code is not
        self.assertEqual(subprocess.run(['sudo', '-n', 'test', '-d', self.run_dir]).returncode, 0)  # nor is the directory

    def test_a_relay_that_never_binds_its_socket_fails_the_start_loudly_and_is_not_left_running(self):
        self.stand_in(binds=False)
        r = self.rc('start')
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('did not create', r.stdout + r.stderr)
        status = self.rc('status')
        self.assertNotEqual(status.returncode, 0, status.stdout)  # not reported as started
        leftover = subprocess.run(['pgrep', '-u', 'fca-egress', '-f', 'fca_egress_relay.py'], capture_output=True, text=True).stdout.split()
        self.assertEqual(leftover, [])

    def test_start_pre_twice_is_idempotent_and_corrects_a_loosened_directory(self):
        self.stand_in(binds=True)
        script = ('eerror() { echo "E: $*" >&2; }; PATH="%s:$PATH"; . "%s"; relay_root="%s"; run_dir="%s"; log_file="%s/unit.log"; '
                  'start_pre; echo first=$?; chmod 0755 "$run_dir"; start_pre; echo second=$?'
                  % (RC_BIN, BODY, self.relay_dir, self.run_dir, self.tmp))
        r = subprocess.run(['sudo', '-n', 'sh', '-c', script], capture_output=True, text=True, timeout=60)
        self.assertEqual([l for l in r.stdout.split() if l.startswith(('first=', 'second='))], ['first=0', 'second=0'], r.stdout + r.stderr)
        self.assertEqual(self.dir_state(), (['group::---', 'mask::--x', 'other::---', 'user::rwx', 'user:agent-deepseek:--x'], 'fca-egress:fca-egress'))


class RehearsalGate(unittest.TestCase):
    """The gate in front of the RealOpenRC tests, tested as pure logic: none of these runs openrc-run."""
    VAR = {DISPOSABLE_VAR: DISPOSABLE_VALUE}

    def gate(self, env, present=(OPENRC_RUN,), sudo=True, identities=True):
        return rehearsal_gate(env, lambda p: p in present, lambda: sudo, lambda: identities)

    def test_no_openrc_on_the_host_is_a_named_skip(self):
        verdict, msg = self.gate({}, present=())
        self.assertEqual(verdict, 'skip')
        self.assertIn('SKIPPED', msg)

    def test_openrc_present_and_no_statement_is_a_refusal_that_names_the_hazard(self):
        verdict, msg = self.gate({})
        self.assertEqual(verdict, 'refuse')
        for word in ('REFUSED', 'identity-proxy', 'DISPOSABLE', DISPOSABLE_VAR, 'failure on purpose'):
            self.assertIn(word, msg)

    def test_a_loose_or_wrong_statement_does_not_count(self):
        for value in ('', '1', 'yes', 'true', DISPOSABLE_VALUE.upper(), DISPOSABLE_VALUE + ' '):
            self.assertEqual(self.gate({DISPOSABLE_VAR: value})[0], 'refuse', value)

    def test_the_statement_is_overridden_by_any_production_service_on_the_host(self):
        for marker in PRODUCTION_MARKERS:
            verdict, msg = self.gate(self.VAR, present=(OPENRC_RUN, marker))
            self.assertEqual(verdict, 'refuse', marker)
            self.assertIn(marker, msg)

    def test_only_the_exact_statement_on_a_clean_host_runs(self):
        self.assertEqual(self.gate(self.VAR), ('run', ''))
        self.assertEqual(self.gate(self.VAR, sudo=False)[0], 'skip')
        self.assertEqual(self.gate(self.VAR, identities=False)[0], 'skip')

    def test_the_real_tests_ask_the_gate_before_anything_else_in_setup(self):
        src = read(__file__)
        setup = src[src.index('class RealOpenRC'):]
        setup = setup[setup.index('def setUp'):setup.index('def tearDown')]
        self.assertIn('rehearsal_gate(', setup)
        self.assertLess(setup.index('rehearsal_gate('), setup.index('mkdtemp'))
        self.assertLess(setup.index('rehearsal_gate('), setup.index('subprocess'))


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
