#!/usr/bin/python3 -I
"""Fixed-upstream TLS passthrough relay for the sterile FCA DSH worker (SOURCE candidate; not provisioned).

Runs on the HOST as a dedicated unprivileged identity (no Aura/service identity, no cortex membership, no supplementary groups).
Listens ONLY on a filesystem Unix socket (no TCP listener). The worker's network namespace has no network at all; a shim inside it
(fca_egress_shim.py) copies bytes from 127.0.0.1:443 to this socket. This relay is the enforcement point.

What it does, in order, per connection:
  1. SO_PEERCRED must be the worker uid (defence in depth over the socket ACL).
  2. Read exactly ONE bounded TLS record, which must be a complete ClientHello; the server_name must be exactly UPSTREAM_HOST.
     No other upstream can be named: there is no CONNECT, SOCKS, URL, config, environment or argv selector. Not even a flag.
  3. Resolve UPSTREAM_HOST itself; every answer must be a public address (private/loopback/link-local/tailnet/CGNAT/ULA/mapped/
     NAT64/6to4/Teredo are refused) and the connection goes to a validated literal address on port 443 only.
  4. Replay the ClientHello and copy opaque bytes both ways. TLS is NEVER terminated: the client verifies the provider certificate
     and hostname itself. This module never loads a TLS library and never holds key material or plaintext.
Fail closed everywhere: malformed or fractured input, resolver or connect failure, upstream close, any deadline or byte bound.
Logs carry fixed reason codes and counters only (never SNI, addresses, headers, bodies, ClientHello bytes or key material).
"""
import ipaddress
import os
import select
import socket
import stat
import struct
import subprocess
import sys
import threading
import time

UPSTREAM_HOST = 'api.neuralwatt.com'
UPSTREAM_PORT = 443
SOCKET_DIR = '/run/fca-dsh-egress'
SOCKET_PATH = SOCKET_DIR + '/relay.sock'
WORKER_UID = 2012
FORBIDDEN_IDS = frozenset({0, 1000, 2000, 2012})  # root, gille, cortex, worker: the relay must be none of these
HELLO_DEADLINE = 5.0
CONNECT_DEADLINE = 5.0
IDLE_DEADLINE = 60.0
TOTAL_DEADLINE = 900.0
MAX_CONCURRENT = 4
MAX_DIRECTION_BYTES = 64 * 1024 * 1024
CHUNK = 16384
MAX_RECORD = 16384
BANNED_EXTENSIONS = frozenset({0xfe0d, 0xfe0a, 0xfe09, 0xfe08, 0xff03, 0xffce})  # ECH / ESNI: would hide the real name
DENY_NETWORKS = tuple(ipaddress.ip_network(n) for n in (
    '100.64.0.0/10', '192.0.0.0/24', '198.18.0.0/15', '240.0.0.0/4', '64:ff9b::/96', '64:ff9b:1::/48', '2002::/16',
    '2001::/32', 'fc00::/7', 'fe80::/10', '100::/64', '2001:db8::/32', '::ffff:0:0/96'))
REASONS = frozenset({'peer', 'busy', 'hello', 'sni', 'dns', 'dnsaddr', 'connect', 'peername', 'idle', 'total', 'bytes', 'closed', 'ok'})


class Reject(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class _Reader:
    def __init__(self, data):
        self.d, self.i = data, 0

    def take(self, n):
        if n < 0 or self.i + n > len(self.d):
            raise Reject('hello')
        out = self.d[self.i:self.i + n]
        self.i += n
        return out

    def u8(self):
        return self.take(1)[0]

    def u16(self):
        return struct.unpack('>H', self.take(2))[0]

    def u24(self):
        return struct.unpack('>I', b'\0' + self.take(3))[0]

    def done(self):
        return self.i == len(self.d)


def parse_client_hello_sni(record):
    """Validate one complete TLS record holding a complete ClientHello; return the single server_name (lower-case ASCII)."""
    if len(record) < 5 or record[0] != 0x16 or record[1] != 3 or record[2] not in (1, 2, 3):
        raise Reject('hello')
    length = struct.unpack('>H', record[3:5])[0]
    if not 4 <= length <= MAX_RECORD or len(record) != 5 + length:
        raise Reject('hello')  # includes a ClientHello fractured over several records, and trailing bytes
    r = _Reader(record[5:])
    if r.u8() != 1 or r.u24() != length - 4:
        raise Reject('hello')
    r.take(2)
    r.take(32)
    sid = r.u8()
    if sid > 32:
        raise Reject('hello')
    r.take(sid)
    suites = r.u16()
    if suites < 2 or suites % 2:
        raise Reject('hello')
    r.take(suites)
    comp = r.u8()
    if comp < 1:
        raise Reject('hello')
    r.take(comp)
    ext_len = r.u16()
    ext = _Reader(r.take(ext_len))
    if not r.done():
        raise Reject('hello')
    seen, names = set(), []
    while not ext.done():
        etype, elen = ext.u16(), ext.u16()
        body = ext.take(elen)
        if etype in seen or etype in BANNED_EXTENSIONS:
            raise Reject('sni')
        seen.add(etype)
        if etype == 0:
            lst = _Reader(body)
            inner = _Reader(lst.take(lst.u16()))
            if not lst.done():
                raise Reject('sni')
            while not inner.done():
                if inner.u8() != 0:
                    raise Reject('sni')
                names.append(inner.take(inner.u16()))
    if len(names) != 1:
        raise Reject('sni')
    name = names[0]
    if not 1 <= len(name) <= 253 or any(c not in b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.' for c in name):
        raise Reject('sni')
    if name.startswith(b'.') or name.endswith(b'.') or b'..' in name:
        raise Reject('sni')
    return name.decode('ascii').lower()


def address_allowed(text):
    """True only for a plain public unicast IPv4/IPv6 literal (no scope id, no mapped/translated/tunnel forms)."""
    if not isinstance(text, str) or '%' in text:
        return False
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return False
    if ip.is_multicast or not ip.is_global:
        return False
    return not any(ip in net for net in DENY_NETWORKS)


def default_resolver(host, port):
    return [ai[4][0] for ai in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


def default_connector(address, port, timeout):
    family = socket.AF_INET6 if ':' in address else socket.AF_INET
    s = socket.socket(family, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        s.connect((address, port))
        return s
    except BaseException:
        s.close()
        raise


class Relay:
    """Production code builds Relay(SOCKET_PATH). Tests may inject resolver/connector/peer_uid and shorter bounds; nothing is
    selectable at run time (no argv, environment or file configuration is read anywhere in this module)."""

    def __init__(self, path=SOCKET_PATH, peer_uid=WORKER_UID, resolver=default_resolver, connector=default_connector,
                 hello_deadline=HELLO_DEADLINE, connect_deadline=CONNECT_DEADLINE, idle_deadline=IDLE_DEADLINE,
                 total_deadline=TOTAL_DEADLINE, max_concurrent=MAX_CONCURRENT, max_bytes=MAX_DIRECTION_BYTES, log=None):
        self.path, self.peer_uid, self.resolver, self.connector = path, peer_uid, resolver, connector
        self.hello_deadline, self.connect_deadline = hello_deadline, connect_deadline
        self.idle_deadline, self.total_deadline, self.max_bytes = idle_deadline, total_deadline, max_bytes
        self.slots = threading.BoundedSemaphore(max_concurrent)
        self.resolving = threading.Lock()
        self.counters = {code: 0 for code in REASONS}
        self.log = log or (lambda line: print(line, file=sys.stderr, flush=True))
        self.listener = None
        self.stopping = False

    def note(self, code):
        assert code in REASONS
        self.counters[code] += 1
        self.log('event=%s total=%d' % (code, self.counters[code]))

    # -- listener -----------------------------------------------------------------------------------------------------
    def bind(self):
        directory = os.path.dirname(self.path)
        st = os.lstat(directory)
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o027:
            raise SystemExit('refused: socket directory must be a real directory owned by the relay identity, no other access')
        try:
            st = os.lstat(self.path)
        except FileNotFoundError:
            st = None
        if st is not None:
            if not stat.S_ISSOCK(st.st_mode):
                raise SystemExit('refused: socket path exists and is not a socket')
            probe = socket.socket(socket.AF_UNIX)
            try:
                probe.settimeout(1)
                probe.connect(self.path)
            except OSError:
                os.unlink(self.path)
            else:
                raise SystemExit('refused: a relay is already listening')
            finally:
                probe.close()
        old = os.umask(0o177)
        try:
            self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.listener.bind(self.path)
        finally:
            os.umask(old)
        os.chmod(self.path, 0o600)
        if self.peer_uid is not None and os.geteuid() != self.peer_uid:
            subprocess.run(['/usr/bin/setfacl', '-m', 'u:%d:rw-' % self.peer_uid, self.path], check=True, env={},
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        self.listener.listen(8)

    def serve_forever(self):
        while not self.stopping:
            try:
                conn, _ = self.listener.accept()
            except OSError:
                return
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def stop(self):
        self.stopping = True
        try:
            self.listener.close()
        except OSError:
            pass
        try:
            os.unlink(self.path)
        except OSError:
            pass

    # -- one connection -----------------------------------------------------------------------------------------------
    def _read_exact(self, conn, n, deadline):
        out = b''
        while len(out) < n:
            left = deadline - time.monotonic()
            if left <= 0:
                raise Reject('hello')
            conn.settimeout(left)
            try:
                chunk = conn.recv(n - len(out))  # plain recv: ancillary data (fds) is discarded by the kernel, never accepted
            except (socket.timeout, OSError):
                raise Reject('hello')
            if not chunk:
                raise Reject('hello')
            out += chunk
        return out

    def _resolve(self):
        if not self.resolving.acquire(timeout=self.connect_deadline):  # wait for a lookup already in flight; refuse only if it outlasts the deadline
            raise Reject('dns')  # one lookup at a time; a stuck resolver cannot pile up threads
        box = {}

        def work():
            try:
                box['v'] = list(self.resolver(UPSTREAM_HOST, UPSTREAM_PORT))
            except BaseException:
                box['e'] = True
            finally:
                self.resolving.release()

        t = threading.Thread(target=work, daemon=True)
        t.start()
        t.join(self.connect_deadline)
        if 'v' not in box or not box['v']:
            raise Reject('dns')
        out = []
        for a in box['v']:
            if not address_allowed(a):
                raise Reject('dnsaddr')  # one bad answer poisons the whole set (rebinding / split-horizon)
            if a not in out:
                out.append(a)
        return out

    def _connect(self, addresses):
        end = time.monotonic() + self.connect_deadline
        for address in addresses:
            left = end - time.monotonic()
            if left <= 0:
                break
            try:
                up = self.connector(address, UPSTREAM_PORT, left)
            except (OSError, socket.timeout):
                continue
            try:
                peer = up.getpeername()[0]
                if ipaddress.ip_address(peer) != ipaddress.ip_address(address):
                    raise Reject('peername')
            except (OSError, ValueError):
                up.close()
                raise Reject('peername')
            except Reject:
                up.close()
                raise
            return up
        raise Reject('connect')

    def handle(self, conn):
        if not self.slots.acquire(blocking=False):
            self.note('busy')
            conn.close()
            return
        up = None
        try:
            cred = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
            if self.peer_uid is not None and struct.unpack('3i', cred)[1] != self.peer_uid:
                raise Reject('peer')
            deadline = time.monotonic() + self.hello_deadline
            header = self._read_exact(conn, 5, deadline)
            if header[0] != 0x16:
                raise Reject('hello')
            n = struct.unpack('>H', header[3:5])[0]
            if not 4 <= n <= MAX_RECORD:
                raise Reject('hello')
            record = header + self._read_exact(conn, n, deadline)
            if parse_client_hello_sni(record) != UPSTREAM_HOST:
                raise Reject('sni')
            up = self._connect(self._resolve())
            up.settimeout(self.connect_deadline)
            up.sendall(record)
            self.note(self._pump(conn, up))
        except Reject as r:
            self.note(r.code)
        except OSError:
            self.note('closed')
        finally:
            for s in (up, conn):
                if s is not None:
                    try:
                        s.close()
                    except OSError:
                        pass
            self.slots.release()

    def _pump(self, a, b):
        start = time.monotonic()
        sent = {a: 0, b: 0}
        open_ = {a, b}
        peer = {a: b, b: a}
        for s in (a, b):
            s.setblocking(True)
        while open_:
            now = time.monotonic()
            if now - start >= self.total_deadline:
                return 'total'
            ready, _, _ = select.select(list(open_), [], [], min(self.idle_deadline, self.total_deadline - (now - start)))
            if not ready:
                return 'idle' if time.monotonic() - start < self.total_deadline else 'total'
            for s in ready:
                try:
                    s.settimeout(self.idle_deadline)
                    chunk = s.recv(CHUNK)
                except (socket.timeout, OSError):
                    return 'closed'
                if not chunk:
                    open_.discard(s)
                    try:
                        peer[s].shutdown(socket.SHUT_WR)
                    except OSError:
                        pass
                    continue
                sent[s] += len(chunk)
                if sent[s] > self.max_bytes:
                    return 'bytes'
                try:
                    peer[s].settimeout(self.idle_deadline)
                    peer[s].sendall(chunk)
                except (socket.timeout, OSError):
                    return 'closed'
        return 'ok'


def _harden():
    if os.geteuid() in FORBIDDEN_IDS or os.getegid() in FORBIDDEN_IDS or os.getuid() != os.geteuid() or os.getgid() != os.getegid():
        raise SystemExit('refused: relay must run as its own dedicated unprivileged identity')
    if set(os.getgroups()) - {os.getegid()}:
        raise SystemExit('refused: relay must have no supplementary groups')
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0 or libc.prctl(4, 0, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS, PR_SET_DUMPABLE=0
        raise SystemExit('refused: could not set no_new_privs/undumpable')


def main(argv):
    if len(argv) != 1:
        print('refused: this relay takes no arguments and reads no configuration', file=sys.stderr)
        return 2
    _harden()
    relay = Relay()
    relay.bind()
    relay.serve_forever()
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
