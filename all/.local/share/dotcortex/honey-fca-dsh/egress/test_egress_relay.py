#!/usr/bin/python3
"""Adversarial tests for fca_egress_relay.py. Synthetic local TLS fixtures and injected resolver/connector are used IN TESTS ONLY;
no provider credential, no live model request, no outbound network. Usage: test_egress_relay.py [DIR_WITH_RELAY_MODULE]"""
import hashlib
import importlib.util
import os
import re
import secrets
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import warnings

warnings.simplefilter('ignore', ResourceWarning)
import faulthandler
faulthandler.dump_traceback_later(int(os.environ.get('FCA_TEST_WATCHDOG', '180')), exit=True)  # a stall names itself instead of hanging
HERE = os.path.dirname(os.path.abspath(__file__))
MODDIR = sys.argv.pop(1) if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else HERE
spec = importlib.util.spec_from_file_location('fca_egress_relay', os.path.join(MODDIR, 'fca_egress_relay.py'))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
HOST = R.UPSTREAM_HOST
PUBLIC = '93.184.216.34'
TMP = tempfile.mkdtemp(prefix='fca-egress-test-')


def sh(*argv):
    subprocess.run(argv, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_pki():
    sh('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', TMP + '/ca.key', '-out', TMP + '/ca.pem',
       '-subj', '/CN=fca-synthetic-test-ca', '-days', '2', '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    for tag, name in (('good', HOST), ('wrongname', 'other.example.test')):
        sh('openssl', 'req', '-newkey', 'rsa:2048', '-nodes', '-keyout', TMP + '/%s.key' % tag, '-out', TMP + '/%s.csr' % tag,
           '-subj', '/CN=' + name)
        with open(TMP + '/%s.ext' % tag, 'w') as f:
            f.write('subjectAltName=DNS:%s\n' % name)
        sh('openssl', 'x509', '-req', '-in', TMP + '/%s.csr' % tag, '-CA', TMP + '/ca.pem', '-CAkey', TMP + '/ca.key',
           '-CAcreateserial', '-out', TMP + '/%s.pem' % tag, '-days', '2', '-extfile', TMP + '/%s.ext' % tag)
    sh('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', TMP + '/ca2.key', '-out', TMP + '/ca2.pem',
       '-subj', '/CN=unrelated-ca', '-days', '2')


# ---- ClientHello builders --------------------------------------------------------------------------------------------------
def real_hello(name=HOST, verify=True):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    inb, outb = ssl.MemoryBIO(), ssl.MemoryBIO()
    obj = ctx.wrap_bio(inb, outb, server_hostname=name)
    try:
        obj.do_handshake()
    except ssl.SSLWantReadError:
        pass
    return outb.read()


def sni_ext(*names):
    entries = b''.join(b'\0' + struct.pack('>H', len(n)) + n for n in names)
    lst = struct.pack('>H', len(entries)) + entries
    return struct.pack('>HH', 0, len(lst)) + lst


def build_hello(exts=None, name=HOST.encode(), sid=b'', trailing=b'', hs_type=1, rec_type=0x16, split_at=None):
    exts = [sni_ext(name)] if exts is None else exts
    body = b'\x03\x03' + os.urandom(32) + bytes([len(sid)]) + sid + b'\0\x02\x13\x01' + b'\1\0'
    e = b''.join(exts)
    body += struct.pack('>H', len(e)) + e
    hs = bytes([hs_type]) + struct.pack('>I', len(body))[1:] + body + trailing
    if split_at:
        a, b = hs[:split_at], hs[split_at:]
        return (bytes([rec_type]) + b'\3\1' + struct.pack('>H', len(a)) + a +
                bytes([rec_type]) + b'\3\1' + struct.pack('>H', len(b)) + b)
    return bytes([rec_type]) + b'\3\1' + struct.pack('>H', len(hs)) + hs


# ---- mock upstream and relay harness -------------------------------------------------------------------------------------------
class MockUpstream:
    def __init__(self, certtag='good', mode='echo'):
        self.mode, self.sock = mode, socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(TMP + '/%s.pem' % certtag, TMP + '/%s.key' % certtag)
        self.held = []
        self.requests = []
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            try:
                c, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self.one, args=(c,), daemon=True).start()

    def one(self, c):
        try:
            if self.mode == 'silent':
                self.held.append(c)
                return
            t = self.ctx.wrap_socket(c, server_side=True)
            buf = b''
            while b'\r\n\r\n' not in buf:
                d = t.recv(4096)
                if not d:
                    return
                buf += d
            self.requests.append(buf)
            if self.mode == 'close-after-request':
                t.close()  # TCP FIN with NO TLS close_notify: a truncation as the relay sees it. The request was read first, so this can never be a RST.
                return
            if self.mode == 'reset-after-request':
                t.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                t.close()  # TCP RST
                return
            if self.mode == 'firehose':
                while True:
                    t.sendall(b'x' * 8192)
            t.sendall(b'mock-ok ' + hashlib.sha256(buf).hexdigest().encode())
            t.close()
        except (OSError, ssl.SSLError):
            pass

    def close(self):
        self.sock.close()
        for c in self.held:
            c.close()


class RawUpstream:
    """Not TLS: reads exactly the forwarded ClientHello record, then sends `payload` and ends the connection with a FIN or a RST.
    Deterministic: the close happens only after the hello was read and nothing else is pending."""
    def __init__(self, payload, how='fin'):
        self.payload, self.how, self.sock = payload, how, socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            try:
                c, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self.one, args=(c,), daemon=True).start()

    def one(self, c):
        try:
            head = b''
            while len(head) < 5:
                head += c.recv(5 - len(head))
            need = struct.unpack('>H', head[3:5])[0]
            while need:
                need -= len(c.recv(need))
            c.sendall(self.payload)
            if self.how == 'rst':
                c.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            else:
                c.shutdown(socket.SHUT_WR)
            c.close()
        except OSError:
            pass

    def close(self):
        self.sock.close()


class Up:
    """Socket proxy: the connector is injected in tests only; getpeername reports the validated address."""
    def __init__(self, s, address):
        self._s, self._a = s, address

    def getpeername(self):
        return (self._a, 443)

    def fileno(self):
        return self._s.fileno()

    def __getattr__(self, n):
        return getattr(self._s, n)


class Harness:
    def __init__(self, upstream=None, resolver=None, connector=None, **kw):
        self.dir = tempfile.mkdtemp(prefix='sock', dir=TMP)
        os.chmod(self.dir, 0o700)
        self.path = self.dir + '/relay.sock'
        self.logs, self.calls, self.upstream = [], [], upstream
        self.resolver = resolver or (lambda h, p: [PUBLIC])

        def connector_default(addr, port, timeout):
            self.calls.append((addr, port))
            if upstream is None:
                raise OSError('no upstream')
            return Up(socket.create_connection(('127.0.0.1', upstream.port), timeout), addr)
        self.relay = R.Relay(self.path, peer_uid=os.getuid(), resolver=self.resolver, connector=connector or connector_default,
                             log=self.logs.append, **kw)
        self.relay.bind()
        self.thread = threading.Thread(target=self.relay.serve_forever, daemon=True)
        self.thread.start()

    def tls(self, name=HOST, cafile='ca.pem', request=b'GET /canary HTTP/1.1\r\nHost: x\r\n\r\n', timeout=10):
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(timeout)
        s.connect(self.path)
        ctx = ssl.create_default_context(cafile=TMP + '/' + cafile)
        t = ctx.wrap_socket(s, server_hostname=name)
        t.sendall(request)
        out = b''
        while True:
            d = t.recv(4096)
            if not d:
                break
            out += d
        return out

    def raw(self, data=b'', pause=0):
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(10)
        s.connect(self.path)
        if data:
            try:
                s.sendall(data)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the relay refused (and closed) before all our bytes were written: that IS the outcome under test, callers check it with closed_within
        return s

    def closed_within(self, s, secs):
        s.settimeout(secs)
        try:
            return s.recv(1) == b''
        except socket.timeout:
            return False
        except OSError:
            return True

    def close(self):
        self.relay.stop()
        if self.upstream:
            self.upstream.close()


class Base(unittest.TestCase):
    def setUp(self):
        self.h = []

    def harness(self, **kw):
        h = Harness(**kw)
        self.h.append(h)
        return h

    def tearDown(self):
        for h in self.h:
            h.close()

    @staticmethod
    def wait_for(predicate, secs=15):
        """Event-driven waiting: poll a condition instead of sleeping for a guessed time (a loaded host is slow, never wrong)."""
        end = time.monotonic() + secs
        while time.monotonic() < end:
            if predicate():
                return True
            time.sleep(0.02)
        return predicate()


class SniParser(unittest.TestCase):
    def test_real_openssl_hello_accepted(self):
        self.assertEqual(R.parse_client_hello_sni(real_hello()), HOST)

    def test_wrong_and_lookalike_names_rejected_by_policy_not_parser(self):
        for n in ('api.neuralwatt.com.evil.test', 'evil.api.neuralwatt.com', 'neuralwatt.com', 'api.neuralwatt.co'):
            self.assertNotEqual(R.parse_client_hello_sni(real_hello(n)), HOST)

    def test_uppercase_name_normalised(self):
        self.assertEqual(R.parse_client_hello_sni(build_hello(name=b'API.NeuralWatt.COM')), HOST)

    def test_missing_sni_and_ip_literal_rejected(self):
        for h in (build_hello(exts=[struct.pack('>HH', 10, 4) + b'\0\2\0\x1d']), real_hello('203.0.113.9')):
            with self.assertRaises(R.Reject):
                R.parse_client_hello_sni(h)

    def test_structural_attacks_rejected(self):
        bad = {
            'trailing dot': build_hello(name=HOST.encode() + b'.'),
            'nul in name': build_hello(name=HOST.encode() + b'\0evil'),
            'two names': build_hello(exts=[sni_ext(HOST.encode(), b'evil.test')]),
            'duplicate sni ext': build_hello(exts=[sni_ext(HOST.encode()), sni_ext(HOST.encode())]),
            'duplicate other ext': build_hello(exts=[sni_ext(HOST.encode()), struct.pack('>HH', 10, 4) + b'\0\2\0\x1d',
                                                     struct.pack('>HH', 10, 4) + b'\0\2\0\x1d']),
            'bytes after the record': build_hello() + b'\0',
            'ech': build_hello(exts=[sni_ext(HOST.encode()), struct.pack('>HH', 0xfe0d, 2) + b'\0\0']),
            'esni': build_hello(exts=[sni_ext(HOST.encode()), struct.pack('>HH', 0xffce, 0)]),
            'fractured over two records': build_hello(split_at=20),
            'trailing bytes in record': build_hello(trailing=b'\0'),
            'not a clienthello': build_hello(hs_type=2),
            'not a handshake record': build_hello(rec_type=0x17),
            'sslv2 style': b'\x80\x2e\x01\x03\x01' + b'\0' * 40,
            'plaintext http': b'CONNECT evil.test:443 HTTP/1.1\r\nHost: evil.test\r\n\r\n',
            'oversize record': b'\x16\x03\x01\x40\x01' + b'\1' * 16385,
            'long session id': build_hello(sid=b'\0' * 33),
            'empty name': build_hello(name=b''),
        }
        for label, hello in bad.items():
            with self.subTest(label), self.assertRaises(R.Reject):
                R.parse_client_hello_sni(hello)

    def test_every_truncation_and_random_mutation_only_ever_rejects(self):
        good = real_hello()
        for n in range(len(good)):
            with self.assertRaises(R.Reject):
                R.parse_client_hello_sni(good[:n])
        rnd = secrets.SystemRandom(7)
        for _ in range(6000):
            b = bytearray(good)
            for _ in range(rnd.randint(1, 4)):
                b[rnd.randrange(len(b))] = rnd.randrange(256)
            try:
                R.parse_client_hello_sni(bytes(b))
            except R.Reject:
                pass  # any other exception type fails the test


class AddressPolicy(unittest.TestCase):
    def test_table(self):
        denied = ['127.0.0.1', '10.1.2.3', '172.16.0.1', '192.168.1.1', '169.254.169.254', '100.64.0.1', '100.64.0.1', '0.0.0.0',
                  '224.0.0.1', '255.255.255.255', '192.0.2.1', '198.18.0.1', '::1', '::', 'fe80::1', 'fe80::1%eth0', 'fd7a:115c:a1e0::1',
                  'fc00::1', '::ffff:127.0.0.1', '::ffff:93.184.216.34', '64:ff9b::7f00:1', '2002:7f00:1::', '2001:0::1', 'ff02::1',
                  '2001:db8::1', 'not-an-ip', '', '93.184.216.34/32', '1.2.3']
        for a in denied:
            with self.subTest(a):
                self.assertFalse(R.address_allowed(a))
        for a in ('93.184.216.34', '104.18.6.80', '2606:4700:20::681a:650'):
            with self.subTest(a):
                self.assertTrue(R.address_allowed(a))
        self.assertFalse(R.address_allowed(None))


class RelayBehaviour(Base):
    def test_positive_end_to_end_and_certificate_is_the_providers(self):
        up = MockUpstream()
        h = self.harness(upstream=up)
        out = h.tls()
        self.assertTrue(out.startswith(b'mock-ok '))
        self.assertEqual(h.calls, [(PUBLIC, 443)])  # the only connect: the validated address, port 443
        self.assertEqual(len(up.requests), 1)

    def test_relay_does_not_terminate_tls_client_verification_still_bites(self):
        h = self.harness(upstream=MockUpstream())
        with self.assertRaises(ssl.SSLCertVerificationError):
            h.tls(cafile='ca2.pem')  # a client that does not trust the provider CA fails: the relay holds no cert of its own
        h2 = self.harness(upstream=MockUpstream(certtag='wrongname'))
        with self.assertRaises(ssl.SSLCertVerificationError):
            h2.tls()  # provider presents a certificate for another name: hostname verification still fails end to end

    def test_wrong_sni_closed_before_any_upstream_contact(self):
        h = self.harness(upstream=MockUpstream())
        for hello in (real_hello('evil.example.test'), real_hello('api.neuralwatt.com.evil.test'), real_hello('203.0.113.9'),
                      build_hello(exts=[sni_ext(HOST.encode()), struct.pack('>HH', 0xfe0d, 0)]), build_hello(split_at=30),
                      b'CONNECT evil.test:443 HTTP/1.1\r\n\r\n', b'\x00' * 64, os.urandom(300)):
            s = h.raw(hello)
            self.assertTrue(h.closed_within(s, 3))
            s.close()
        self.assertEqual(h.calls, [])

    def test_dns_answers_private_or_mixed_refused_without_connect(self):
        for answers in (['127.0.0.1'], ['10.0.0.5'], ['100.64.0.1'], ['169.254.1.1'], ['fd7a:115c:a1e0::5'], ['::1'],
                        [PUBLIC, '10.0.0.5'], ['::ffff:10.0.0.5'], []):
            h = self.harness(upstream=MockUpstream(), resolver=lambda host, port, a=answers: a)
            s = h.raw(real_hello())
            self.assertTrue(h.closed_within(s, 3), answers)
            self.assertEqual(h.calls, [], answers)

    def test_resolver_hang_and_failure_are_bounded(self):
        gate = threading.Event()
        h = self.harness(upstream=MockUpstream(), resolver=lambda host, port: gate.wait(30), connect_deadline=0.5)
        t0 = time.monotonic()
        s = h.raw(real_hello())
        self.assertTrue(h.closed_within(s, 3))
        self.assertLess(time.monotonic() - t0, 2.5)
        s2 = h.raw(real_hello())  # lookup still stuck: refused immediately, no thread pile-up
        self.assertTrue(h.closed_within(s2, 1))
        gate.set()

        def boom(host, port):
            raise OSError('dns down')
        h2 = self.harness(upstream=MockUpstream(), resolver=boom)
        self.assertTrue(h2.closed_within(h2.raw(real_hello()), 3))

    def test_connect_failure_and_peername_mismatch_fail_closed(self):
        h = self.harness(upstream=None)
        self.assertTrue(h.closed_within(h.raw(real_hello()), 3))
        up = MockUpstream()
        h2 = self.harness(upstream=up, connector=lambda a, p, t: socket.create_connection(('127.0.0.1', up.port), t))
        self.assertTrue(h2.closed_within(h2.raw(real_hello()), 3))  # connector returned a socket to an address we did not validate

    def test_slowloris_and_silent_connect_hit_hello_deadline(self):
        h = self.harness(upstream=MockUpstream(), hello_deadline=0.8)
        s = h.raw()
        self.assertTrue(h.closed_within(s, 3))
        hello = real_hello()
        s = h.raw()
        t0 = time.monotonic()
        try:
            for b in hello[:40]:
                s.sendall(bytes([b]))
                time.sleep(0.1)
        except OSError:
            pass
        self.assertTrue(h.closed_within(s, 3))
        self.assertLess(time.monotonic() - t0, 3)
        self.assertEqual(h.calls, [])

    def test_concurrency_bound(self):
        up = MockUpstream(mode='silent')
        h = self.harness(upstream=up, max_concurrent=2)
        held = []
        for n in (1, 2):
            held.append(h.raw(real_hello()))
            self.assertTrue(self.wait_for(lambda n=n: len(h.calls) == n))  # one at a time: each slot really is in use before the next connection starts
        extra = h.raw(real_hello())
        self.assertTrue(h.closed_within(extra, 10))
        self.assertEqual(len(h.calls), 2)
        for s in held:
            s.close()

    def test_two_simultaneous_connections_with_a_slow_lookup_are_both_served(self):
        # rev6/rev6c refused the second connection with 'dns' while the first one's lookup was still in flight (found by stress; RED on the old relay).
        slow = lambda host, port: (time.sleep(0.4), [PUBLIC])[1]
        h = self.harness(upstream=MockUpstream(mode='silent'), resolver=slow, max_concurrent=4)
        held = [h.raw(real_hello()), h.raw(real_hello())]
        self.assertTrue(self.wait_for(lambda: len(h.calls) == 2))  # both reached the upstream connect
        self.assertEqual(h.relay.counters['dns'], 0)
        for s in held:
            s.close()

    def test_a_stuck_resolver_under_the_default_four_slots_is_bounded_and_accumulates_nothing(self):
        # What the old non-blocking acquire protected and the bounded wait must NOT trade away (Hermes, rev6d review): with a resolver that never returns, under the DEFAULT
        # four slots, waiters are bounded by connect_deadline, the resolver is invoked once, the connection whose own lookup is stuck returns 'dns' inside the deadline,
        # nothing reaches the upstream, and no thread accumulates, across two waves of connections.
        self.assertEqual(R.MAX_CONCURRENT, 4)
        stuck, started = threading.Event(), []

        def resolver(host, port):
            started.append(1)
            stuck.wait(60)
            return [PUBLIC]
        deadline = 0.6
        h = self.harness(upstream=MockUpstream(mode='silent'), resolver=resolver, connect_deadline=deadline)  # max_concurrent left at the default
        before = threading.active_count()
        for wave in (1, 2):
            t0 = time.monotonic()
            socks = [h.raw(real_hello()) for _ in range(6)]  # 4 can take a slot (one stuck lookup + three waiters); the other two are refused 'busy'
            ended = []
            for s in socks:
                self.assertTrue(h.closed_within(s, 15))
                ended.append(time.monotonic() - t0)
            self.assertLess(max(ended), deadline + 5.0)  # bounded by the deadline plus scheduling slack, never by the resolver's 60 s
            self.assertEqual(len(started), 1)  # no second lookup thread while the first one lives
            self.assertTrue(self.wait_for(lambda: h.relay.counters['dns'] + h.relay.counters['busy'] == 6 * wave))
            self.assertGreaterEqual(h.relay.counters['dns'], 4 * wave)  # cumulative: at most two connections of each wave of six are refused 'busy', the rest are 'dns'
            self.assertEqual(h.calls, [])  # nothing ever reached the upstream
            self.assertTrue(self.wait_for(lambda: threading.active_count() <= before + 1))  # only the one stuck lookup thread outlives the wave
        stuck.set()
        self.assertTrue(self.wait_for(lambda: threading.active_count() <= before))  # and it goes away once the resolver returns

    def test_idle_total_and_byte_deadlines(self):
        up = MockUpstream(mode='silent')
        h = self.harness(upstream=up, idle_deadline=0.6)
        s = h.raw(real_hello())
        self.assertTrue(h.closed_within(s, 4))
        up2 = MockUpstream(mode='firehose')
        h2 = self.harness(upstream=up2, total_deadline=1.0)
        s = h2.raw(real_hello())
        s.settimeout(5)
        got, t0 = 0, time.monotonic()
        try:
            ctx = ssl.create_default_context(cafile=TMP + '/ca.pem')
            t = ctx.wrap_socket(s, server_hostname=HOST)
            t.sendall(b'GET / HTTP/1.1\r\n\r\n')
            while t.recv(65536):
                got += 1
        except (OSError, ssl.SSLError):
            pass
        self.assertLess(time.monotonic() - t0, 4)
        up3 = MockUpstream(mode='firehose')
        h3 = self.harness(upstream=up3, max_bytes=100000)
        ctx = ssl.create_default_context(cafile=TMP + '/ca.pem')
        t = ctx.wrap_socket(h3.raw(), server_hostname=HOST)
        t.sendall(b'GET / HTTP/1.1\r\n\r\n')
        total = 0
        try:
            while True:
                d = t.recv(65536)
                if not d:
                    break
                total += len(d)
        except (OSError, ssl.SSLError):
            pass
        self.assertLess(total, 400000)
        time.sleep(0.3)
        self.assertGreaterEqual(h3.relay.counters['bytes'], 1)

    # ---- upstream truncation: what the worker can and cannot see (EGRESS.md "Close and truncation semantics"). All deterministic: ----
    # ---- the upstream always reads the request first, so a close can only ever be a FIN (or an explicit RST), never a race. ----
    def view(self, h, strict=False):
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(10)
        s.connect(h.path)
        ctx = ssl.create_default_context(cafile=TMP + '/ca.pem')
        t = ctx.wrap_socket(s, server_hostname=HOST, suppress_ragged_eofs=not strict)
        t.sendall(b'GET /canary HTTP/1.1\r\nHost: x\r\n\r\n')
        out = b''
        while True:
            d = t.recv(4096)
            if not d:
                return out
            out += d

    def wait_counter(self, h, code, secs=5):
        end = time.monotonic() + secs
        while time.monotonic() < end and not h.relay.counters[code]:
            time.sleep(0.02)
        return h.relay.counters[code]

    def test_truncation_without_close_notify_is_a_clean_empty_eof_to_a_lenient_client_and_nothing_is_invented(self):
        h = self.harness(upstream=MockUpstream(mode='close-after-request'))
        self.assertEqual(self.view(h), b'')  # documented limit: no exception, and no byte the upstream did not send
        self.assertGreaterEqual(self.wait_counter(h, 'ok'), 1)

    def test_a_strict_client_sees_the_same_truncation_as_an_error_through_the_relay(self):
        h = self.harness(upstream=MockUpstream(mode='close-after-request'))
        with self.assertRaises(ssl.SSLError):
            self.view(h, strict=True)  # TLS is end to end, so the missing close_notify stays visible to a client that checks it

    def test_upstream_reset_ends_both_sides_is_counted_closed_and_delivers_nothing_extra(self):
        h = self.harness(upstream=MockUpstream(mode='reset-after-request'))
        try:
            got = self.view(h)
        except (ssl.SSLError, OSError):
            got = b''
        self.assertEqual(got, b'')
        self.assertGreaterEqual(self.wait_counter(h, 'closed'), 1)

    def test_relay_forwards_exactly_the_upstream_bytes_then_a_fin_even_when_the_last_record_is_incomplete(self):
        payload = b'\x17\x03\x03\x00\x64' + b'abc'  # a record header that promises 100 bytes, only 3 delivered, then FIN
        h = self.harness(upstream=RawUpstream(payload, how='fin'))
        s = h.raw(real_hello())
        got = b''
        while True:
            d = s.recv(4096)
            if not d:
                break
            got += d
        self.assertEqual(got, payload)  # nothing dropped, nothing added, no repair of the half record
        s.close()  # the relay reports 'ok' only when BOTH directions have ended: the client's side is ours to close
        self.assertGreaterEqual(self.wait_counter(h, 'ok'), 1)

    def test_relay_never_delivers_bytes_the_upstream_did_not_send_when_it_resets(self):
        payload = b'\x17\x03\x03\x00\x64' + b'abc'
        h = self.harness(upstream=RawUpstream(payload, how='rst'))
        s = h.raw(real_hello())
        got = b''
        try:
            while True:
                d = s.recv(4096)
                if not d:
                    break
                got += d
        except OSError:
            pass
        self.assertTrue(payload.startswith(got), got)  # whatever arrived is a prefix of what the upstream sent
        self.assertGreaterEqual(self.wait_counter(h, 'closed'), 1)

    def test_fd_passing_is_not_accepted(self):
        up = MockUpstream()
        h = self.harness(upstream=up)
        base = len(os.listdir('/proc/self/fd'))
        for _ in range(20):
            s = h.raw()
            r, w = os.pipe()
            try:
                s.sendmsg([real_hello()], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack('i', r))])
            except OSError:
                pass
            time.sleep(0.05)
            s.close()
            os.close(r)
            os.close(w)
        time.sleep(1.0)
        self.assertLessEqual(len(os.listdir('/proc/self/fd')), base + 3)

    def test_peer_uid_check_rejects_other_uid_even_with_open_permissions(self):
        h = self.harness(upstream=MockUpstream())
        h.relay.peer_uid = os.getuid() + 12345
        os.chmod(h.path, 0o666)
        s = h.raw(real_hello())
        self.assertTrue(h.closed_within(s, 3))
        self.assertEqual(h.calls, [])
        self.assertGreaterEqual(h.relay.counters['peer'], 1)

    def test_logs_contain_only_fixed_codes(self):
        up = MockUpstream()
        h = self.harness(upstream=up)
        canary = 'CANARY-' + secrets.token_hex(8)
        h.tls(request=('GET /%s HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer %s\r\n\r\n' % (canary, canary)).encode())
        s = h.raw(real_hello('secret-name-%s.example.test' % canary[-6:]))
        h.closed_within(s, 2)
        time.sleep(0.2)
        blob = '\n'.join(h.logs)
        self.assertTrue(h.logs)
        for line in h.logs:
            self.assertRegex(line, r'^event=[a-z]+ total=\d+$')
        for forbidden in (canary, 'secret-name', 'neuralwatt', PUBLIC, '16030', 'Bearer'):
            self.assertNotIn(forbidden, blob)

    def test_stale_socket_and_unsafe_directory_refused(self):
        h = self.harness(upstream=MockUpstream())
        again = R.Relay(h.path, peer_uid=os.getuid())
        with self.assertRaises(SystemExit):
            again.bind()  # a live relay owns the path
        d = tempfile.mkdtemp(dir=TMP)
        os.chmod(d, 0o755)
        with self.assertRaises(SystemExit):
            R.Relay(d + '/relay.sock', peer_uid=os.getuid()).bind()
        os.chmod(d, 0o700)
        open(d + '/relay.sock', 'w').close()
        with self.assertRaises(SystemExit):
            R.Relay(d + '/relay.sock', peer_uid=os.getuid()).bind()  # a regular file is never unlinked
        link_target = tempfile.mkdtemp(dir=TMP)
        os.chmod(link_target, 0o700)
        os.symlink(link_target, TMP + '/linkdir')
        with self.assertRaises(SystemExit):
            R.Relay(TMP + '/linkdir/relay.sock', peer_uid=os.getuid()).bind()


class SourceProperties(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(MODDIR, 'fca_egress_relay.py')) as f:
            self.src = f.read()
        head, _, rest = self.src.partition('"""')  # drop the module docstring: it names what is absent
        body = rest.partition('"""')[2]
        self.code = '\n'.join(l for l in body.splitlines() if not l.strip().startswith('#'))

    def test_every_close_reason_is_documented_in_egress_md(self):
        doc = open(os.path.join(HERE, 'EGRESS.md')).read()
        for code in sorted(R.REASONS):
            self.assertIn('| `%s` |' % code, doc, code)
        row = [l for l in doc.splitlines() if l.startswith('| `dns` |')][0]
        self.assertIn('bounded wait', row)  # says when 'dns' fires after the change, not just that it exists

    def test_no_tls_termination_no_selector_no_config(self):
        for pat in (r'\bimport ssl\b', r'\bwrap_socket\b', r'\bSSLContext\b', r'os\.environ', r'os\.getenv', r'argparse', r'sys\.argv\[1',
                    r'\bSOCKS\b', r'\bsocks\b', r'recvmsg', r'SCM_RIGHTS', r'AF_INET.*bind', r'\.bind\(\(', r'verify_mode', r'check_hostname',
                    r'CERT_NONE', r'shell=True', r'open\('):
            self.assertIsNone(re.search(pat, self.code), pat)

    def test_only_unix_listener_and_fixed_constants(self):
        self.assertIn("UPSTREAM_HOST = 'api.neuralwatt.com'", self.src)
        self.assertIn('UPSTREAM_PORT = 443', self.src)
        self.assertEqual(self.src.count('socket.AF_UNIX'), 2)
        self.assertEqual(self.src.count('.listen('), 1)

    def test_main_refuses_arguments(self):
        self.assertEqual(R.main(['relay', '--upstream', 'evil.test:443']), 2)
        self.assertEqual(R.main(['relay', 'x']), 2)

    def test_harden_refuses_forbidden_identities(self):
        if os.geteuid() == 1000:
            with self.assertRaises(SystemExit):
                R._harden()  # the test runner is gille (1000): must be refused as a relay identity


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


make_pki()
if __name__ == '__main__':
    unittest.main(verbosity=1, warnings='ignore')
