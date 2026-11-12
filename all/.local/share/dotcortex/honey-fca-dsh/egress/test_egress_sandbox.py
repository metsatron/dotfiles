#!/usr/bin/python3
"""Real-namespace, real-UID integration test for the FCA egress relay (SOURCE candidate). Needs bwrap and passwordless sudo for
setpriv/install/setfacl (all scratch state is under /tmp and removed). Stand-in identities are bare numeric uids with NO passwd entry:
relay=61999, other=61998; the worker is the real uid 2012 with NO supplementary groups (the post-cortex-removal state).
Synthetic local TLS only; the relay's resolver/connector are injected here only; nothing leaves this host. Usage:
test_egress_sandbox.py [DIR_WITH_MODULES]"""
import faulthandler
import importlib.util
import json
import os
import pwd
import select
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import warnings

warnings.simplefilter('ignore', ResourceWarning)
# A stall must name itself: after FCA_TEST_WATCHDOG seconds (default 300) every thread's traceback is printed and the process exits non-zero.
faulthandler.dump_traceback_later(int(os.environ.get('FCA_TEST_WATCHDOG', '300')), exit=True)
HERE = os.path.dirname(os.path.abspath(__file__))
MODDIR = sys.argv.pop(1) if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else HERE
RELAY_UID, OTHER_UID, WORKER = 61999, 61998, 2012
NODE = '/home/agent-deepseek/.local/share/fca-dsh-runtime/node/bin/node'
WORK = tempfile.mkdtemp(prefix='fca-egress-sbx-')
os.chmod(WORK, 0o755)
LANE, SBX = WORK + '/lane', WORK + '/sbx'
SOCKDIR = WORK + '/sock'
procs, relay_logs = [], []

def _sudo_ok(*argv):
    try:
        return subprocess.run(['sudo', '-n'] + list(argv), capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


node_present = _sudo_ok('test', '-x', NODE)


def honey_preconditions():
    """Why this suite cannot run here, or [] when it can. It needs the real Honey identity: bwrap, passwordless sudo, and uid 2012 = agent-deepseek."""
    problems = []
    if shutil.which('bwrap') is None:
        problems.append('bwrap is not installed')
    if not _sudo_ok('true'):
        problems.append('passwordless sudo is not available')
    try:
        if pwd.getpwuid(WORKER).pw_name != 'agent-deepseek':
            problems.append('uid %d is not agent-deepseek' % WORKER)
    except KeyError:
        problems.append('uid %d does not exist on this host' % WORKER)
    return problems


def sudo_as(uid, *argv, groups=None):
    g = ['--clear-groups'] if groups is None else ['--groups', groups]
    return ['sudo', '-n', 'setpriv', '--reuid=%d' % uid, '--regid=%d' % uid] + g + list(argv)


def run(argv, **kw):
    kw.setdefault('capture_output', True)
    kw.setdefault('text', True)
    kw.setdefault('timeout', 60)
    return subprocess.run(argv, **kw)


def start_relay(sockdir):
    run(['sudo', '-n', 'install', '-d', '-o', str(RELAY_UID), '-g', str(RELAY_UID), '-m', '0700', sockdir], check=True)
    run(['sudo', '-n', 'setfacl', '-m', 'u:%d:--x' % WORKER, sockdir], check=True)
    p = subprocess.Popen(sudo_as(RELAY_UID, '/usr/bin/python3', '-B', '-I', LANE + '/relay_runner.py', LANE, sockdir, PORT),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    procs.append(p)
    lines = []

    def pump():
        for line in p.stderr:
            lines.append(line.strip())
    threading.Thread(target=pump, daemon=True).start()
    if not select.select([p.stdout], [], [], 60)[0]:
        raise AssertionError('relay did not report ready within 60 s; stderr so far: %r' % (lines,))
    ready = p.stdout.readline().strip()
    assert ready == 'relay-ready', (ready, lines)
    return p, lines


def bwrap(sockdir, command, env=None, with_node=False):
    args = ['/usr/bin/bwrap', '--unshare-user', '--unshare-pid', '--unshare-net', '--unshare-ipc', '--unshare-uts', '--unshare-cgroup',
            '--uid', '2012', '--gid', '2012', '--cap-add', 'CAP_NET_BIND_SERVICE',
            '--ro-bind', '/usr', '/usr', '--ro-bind', '/bin', '/bin', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
            '--ro-bind', SBX + '/hosts', '/etc/hosts', '--ro-bind', sockdir, '/run/fca-egress', '--ro-bind', SBX, '/opt/test',
            '--tmpfs', '/tmp', '--proc', '/proc', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
            '--setenv', 'HOME', '/tmp/h']
    # NOT "--dev /dev": with it the kernel denies the in-namespace bind of 443 even though CAP_NET_BIND_SERVICE is held (reproduced
    # 2026-11-06, bwrap 0.11.0, kernel 7.2.0-rc2). The four harmless device nodes are bound individually instead.
    for node in ('null', 'zero', 'urandom', 'random'):
        args += ['--dev-bind', '/dev/' + node, '/dev/' + node]
    if with_node:
        args += ['--dir', '/opt/node', '--dir', '/opt/node/bin', '--ro-bind', NODE, '/opt/node/bin/node']
    for k, v in (env or {}).items():
        args += ['--setenv', k, v]
    return sudo_as(WORKER, *(args + command))


def through_shim(sockdir, mode, **kw):
    return run(bwrap(sockdir, ['/usr/bin/python3', '-I', '/opt/test/fca_egress_shim.py', '--', '/usr/bin/python3', '-I',
                               '/opt/test/sandbox_client.py', mode], **kw))


def real_hello(name):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    inb, outb = ssl.MemoryBIO(), ssl.MemoryBIO()
    try:
        ctx.wrap_bio(inb, outb, server_hostname=name).do_handshake()
    except ssl.SSLWantReadError:
        pass
    return outb.read()


def connect_unix(path, send=None):
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(3)
    try:
        s.connect(path)
        if send:
            s.sendall(send)
            return 'connected-then-' + ('closed' if s.recv(1) == b'' else 'data')
        return 'connected'
    except ConnectionResetError:
        return 'connected-then-closed'  # the relay closed with our bytes unread
    except OSError as e:
        return type(e).__name__
    finally:
        s.close()


def setUpModule():
    global PORT, CANARY, ABSTRACT, relay_proc, relay_log
    problems = honey_preconditions()
    if problems:
        raise unittest.SkipTest('Honey-only suite, skipped here: ' + '; '.join(problems))
    os.makedirs(LANE)
    os.makedirs(SBX)
    for f in ('fca_egress_relay.py', 'relay_runner.py', 'sandbox_mock_upstream.py'):
        shutil.copy(os.path.join(MODDIR, f) if f.startswith('fca_') else os.path.join(HERE, f), LANE)
    for f in ('fca_egress_shim.py', 'sandbox_client.py', 'hosts'):
        shutil.copy(os.path.join(MODDIR, f) if f.startswith('fca_') else os.path.join(HERE, f), SBX)
    for d in (LANE, SBX):
        for f in os.listdir(d):
            os.chmod(os.path.join(d, f), 0o755 if f.endswith('.py') else 0o644)
    key = WORK + '/keys'
    os.makedirs(key, mode=0o700)
    sh = lambda *a: subprocess.run(a, check=True, capture_output=True)
    sh('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key + '/ca.key', '-out', SBX + '/ca.pem', '-subj', '/CN=fca-test-ca',
       '-days', '2', '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    sh('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key + '/ca2.key', '-out', SBX + '/ca2.pem', '-subj', '/CN=unrelated', '-days', '2')
    sh('openssl', 'req', '-newkey', 'rsa:2048', '-nodes', '-keyout', key + '/leaf.key', '-out', key + '/leaf.csr', '-subj', '/CN=api.neuralwatt.com')
    open(key + '/leaf.ext', 'w').write('subjectAltName=DNS:api.neuralwatt.com\n')
    sh('openssl', 'x509', '-req', '-in', key + '/leaf.csr', '-CA', SBX + '/ca.pem', '-CAkey', key + '/ca.key', '-CAcreateserial', '-out', key + '/leaf.pem',
       '-days', '2', '-extfile', key + '/leaf.ext')
    for f in os.listdir(SBX):
        os.chmod(os.path.join(SBX, f), 0o755 if f.endswith('.py') else 0o644)
    up = subprocess.Popen(['/usr/bin/python3', '-I', LANE + '/sandbox_mock_upstream.py', key + '/leaf.pem', key + '/leaf.key', WORK + '/port'])
    procs.append(up)
    for _ in range(50):
        if os.path.exists(WORK + '/port') and open(WORK + '/port').read():
            break
        time.sleep(0.1)
    PORT = open(WORK + '/port').read().strip()
    CANARY = socket.socket()
    CANARY.bind(('127.0.0.1', 0))
    CANARY.listen(4)
    ABSTRACT = socket.socket(socket.AF_UNIX)
    ABSTRACT.bind('\0fca-egress-canary-%d' % os.getpid())
    ABSTRACT.listen(4)
    relay_proc, relay_log = start_relay(SOCKDIR)


def tearDownModule():
    for p in procs:
        run(['sudo', '-n', 'kill', '-9', str(p.pid)], check=False)
        try:
            p.kill()
        except OSError:
            pass
    run(['sudo', '-n', 'pkill', '-9', '-u', str(RELAY_UID)], check=False)
    run(['sudo', '-n', 'rm', '-rf', WORK], check=False)


class Sandbox(unittest.TestCase):
    def test_01_the_operator_is_not_admitted_to_the_relay_socket(self):
        self.assertEqual(connect_unix(SOCKDIR + '/relay.sock'), 'PermissionError')  # gille (uid 1000, in cortex): 0700 dir, ACL only for 2012

    def test_02_direct_network_attempts_stay_blocked_in_the_namespace(self):
        host_lo = socket.create_connection(CANARY.getsockname(), 2)  # control: the canary really listens on the host
        host_lo.close()
        s = socket.socket(socket.AF_UNIX)
        s.connect('\0fca-egress-canary-%d' % os.getpid())
        s.close()
        out = run(bwrap(SOCKDIR, ['/usr/bin/python3', '-I', '/opt/test/sandbox_client.py', 'isolation'],
                        env={'CANARY_PORT': str(CANARY.getsockname()[1]), 'ABSTRACT_NAME': 'fca-egress-canary-%d' % os.getpid()}))
        self.assertEqual(out.returncode, 0, out.stderr)
        res = json.loads(out.stdout)
        for k in ('host_loopback_canary', 'tailnet_22', 'tailnet_3003', 'lan_gateway_80', 'public_v4_443', 'public_v6_443', 'dns_udp_resolver',
                  'host_abstract_socket', 'other_unix_path'):
            self.assertNotEqual(res[k], 'connected', (k, res))
            print('  blocked %-22s %s' % (k, res[k]))
        self.assertEqual(res['resolve_example_com'], 'gaierror')
        self.assertEqual(res['resolve_provider'], ['127.0.0.1'])  # hosts file only: the name never leaves the namespace
        self.assertEqual(res['resolve_provider_alt'], 'gaierror')
        self.assertEqual(res['visible_mounts_run'], ['fca-egress'])
        self.assertFalse(res['home_visible'])

    def test_03_shim_binds_443_then_holds_no_capabilities(self):
        out = through_shim(SOCKDIR, 'caps')
        self.assertEqual(out.returncode, 0, out.stderr)
        res = json.loads(out.stdout)
        self.assertEqual((res['uid'], res['gid']), (2012, 2012))
        self.assertNotIn(2000, res['groups'])
        self.assertNotIn(1000, res['groups'])
        for k in ('CapEff', 'CapPrm', 'CapInh', 'CapAmb'):
            self.assertEqual(int(res[k], 16), 0, res)
        self.assertEqual(res['NoNewPrivs'], '1')
        self.assertEqual(res['listening_443'], 'connected')

    def test_04_positive_transfer_through_the_one_allowed_socket(self):
        out = through_shim(SOCKDIR, 'positive')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)['response'], 'mock-ok ')
        self.assertIn('event=ok total=1', '\n'.join(relay_log))

    def test_05_negative_cases_through_the_real_path(self):
        out = through_shim(SOCKDIR, 'negative')
        self.assertEqual(out.returncode, 0, out.stderr)
        res = json.loads(out.stdout)
        for k, v in res.items():
            self.assertEqual(v, 'closed', (k, res))
        time.sleep(0.3)
        self.assertGreaterEqual(sum('event=sni' in l or 'event=hello' in l for l in relay_log), 5)

    @unittest.skipUnless(node_present, 'DSH runtime Node not staged')
    def test_06_real_dsh_node_client_verifies_the_providers_certificate_end_to_end(self):
        out = through_shim(SOCKDIR, 'node-positive', with_node=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        lines = dict(l.split(':', 1) for l in out.stdout.splitlines())
        self.assertEqual(lines['trusted-ca'], 'mock-ok ')
        self.assertTrue(lines['default-roots'].startswith('ERR:'), lines)  # real Node with real roots rejects the synthetic CA
        self.assertTrue(lines['unrelated-ca'].startswith('ERR:'), lines)
        print('  node:', lines)

    @unittest.skipUnless(node_present, 'DSH runtime Node not staged')
    def test_06b_real_node_sees_truncation_through_http_framing_not_through_tls(self):
        # What the worker can and cannot see when the upstream dies mid-response (EGRESS.md "Close and truncation semantics"). Measured with the
        # real DSH Node through shim, socket and relay. The relay is a byte pump and cannot tell an orderly close from a truncation on a record boundary.
        out = through_shim(SOCKDIR, 'node-truncation', with_node=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        res = dict(l.split(':', 1) for l in out.stdout.splitlines())
        for k in ('content-length-fin', 'content-length-notify', 'chunked-fin'):
            self.assertTrue(res[k].startswith('INCOMPLETE:'), (k, res))  # a short body or a missing chunk terminator is detected by framing
        for k in ('close-delimited-fin', 'close-delimited-notify'):
            self.assertTrue(res[k].startswith('COMPLETE:'), (k, res))  # a close-delimited body cannot be told from a complete one: do not use it
        print('  node truncation:', res)

    def test_07_socket_acl_admits_only_the_worker_uid(self):
        path = SOCKDIR + '/relay.sock'
        probe = ['/usr/bin/python3', '-I', '-c', 'import socket,sys\ns=socket.socket(socket.AF_UNIX)\ntry:\n s.connect(sys.argv[1]);print("connected")\n'
                 'except OSError as e: print(type(e).__name__)', path]
        self.assertEqual(run(probe).stdout.strip(), 'PermissionError')  # gille (uid 1000, in cortex)
        self.assertEqual(run(sudo_as(OTHER_UID, *probe)).stdout.strip(), 'PermissionError')
        self.assertEqual(run(sudo_as(WORKER, *probe)).stdout.strip(), 'connected')
        self.assertEqual(run(sudo_as(WORKER, *probe, groups='2000')).stdout.strip(), 'connected')  # uid, not cortex, is what admits

    def test_08_peer_credential_check_holds_even_if_permissions_are_loosened(self):
        d = WORK + '/sock2'
        p, lines = start_relay(d)
        run(['sudo', '-n', 'setpriv', '--reuid=%d' % RELAY_UID, '--regid=%d' % RELAY_UID, '--clear-groups', '/usr/bin/chmod', '0777', d,
             d + '/relay.sock'], check=True)
        self.assertEqual(connect_unix(d + '/relay.sock', real_hello('api.neuralwatt.com')), 'connected-then-closed')
        time.sleep(0.3)
        self.assertIn('event=peer total=1', '\n'.join(lines))
        self.assertNotIn('event=ok', '\n'.join(lines))
        self.assertEqual(run(sudo_as(WORKER, '/usr/bin/python3', '-I', '-c', 'import socket,sys\ns=socket.socket(socket.AF_UNIX)\ns.connect(sys.argv[1])\n'
                                    's.sendall(bytes.fromhex(sys.argv[2]))\nprint("data" if s.recv(1) else "closed")', d + '/relay.sock',
                                    real_hello('api.neuralwatt.com').hex())).stdout.strip(), 'data')  # the real worker uid is still admitted

    def test_09_relay_refuses_forbidden_identities(self):
        code = ('import importlib.util,sys\nspec=importlib.util.spec_from_file_location("r",sys.argv[1]+"/fca_egress_relay.py")\n'
                'm=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\ntry:\n m._harden();print("accepted")\n'
                'except SystemExit as e: print("refused")')
        cmd = ['/usr/bin/python3', '-B', '-I', '-c', code, LANE]
        self.assertEqual(run(sudo_as(RELAY_UID, *cmd)).stdout.strip(), 'accepted')
        self.assertEqual(run(sudo_as(RELAY_UID, *cmd, groups='2000')).stdout.strip(), 'refused')   # cortex membership carried in
        self.assertEqual(run(sudo_as(RELAY_UID, *cmd, groups='61999,2012')).stdout.strip(), 'refused')  # any supplementary group
        self.assertEqual(run(sudo_as(WORKER, *cmd)).stdout.strip(), 'refused')                    # not the worker itself
        self.assertEqual(run(sudo_as(1000, *cmd)).stdout.strip(), 'refused')                      # not gille
        self.assertEqual(run(['sudo', '-n'] + cmd).stdout.strip(), 'refused')                     # not root

    def test_10_relay_death_and_socket_absence_fail_closed(self):
        t0 = time.monotonic()
        run(['sudo', '-n', 'pkill', '-9', '-f', 'relay_runner.py %s %s ' % (LANE, SOCKDIR)], check=False)
        time.sleep(0.5)
        out = through_shim(SOCKDIR, 'positive')
        self.assertNotEqual(out.returncode, 0)  # TLS handshake fails: the shim closed the connection, nothing fell back
        self.assertNotIn('mock-ok', out.stdout)
        run(['sudo', '-n', 'rm', '-f', SOCKDIR + '/relay.sock'], check=True)
        out = through_shim(SOCKDIR, 'positive')
        self.assertNotEqual(out.returncode, 0)
        self.assertNotIn('mock-ok', out.stdout)
        self.assertLess(time.monotonic() - t0, 40)


if __name__ == '__main__':
    unittest.main(verbosity=2, warnings='ignore')
