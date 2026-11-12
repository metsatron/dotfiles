#!/usr/bin/python3 -I
"""Runs INSIDE the bwrap namespace as uid 2012 (test fixture). Usage: sandbox_client.py isolation|caps|positive|negative|node-positive"""
import json, os, socket, ssl, subprocess, sys

def attempt(fn):
    try:
        fn(); return 'connected'
    except OSError as e:
        return type(e).__name__ + ':' + str(e.errno)
    except Exception as e:
        return type(e).__name__

def tcp(host, port, family=socket.AF_INET):
    s = socket.socket(family); s.settimeout(2); s.connect((host, port)); s.close()

def udp(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(2); s.connect((host, port)); s.send(b'x'); s.close()

def abstract(name):
    s = socket.socket(socket.AF_UNIX); s.settimeout(2); s.connect('\0' + name); s.close()

def path_sock(p):
    s = socket.socket(socket.AF_UNIX); s.settimeout(2); s.connect(p); s.close()

def resolve(name):
    try:
        return sorted({ai[4][0] for ai in socket.getaddrinfo(name, 443, type=socket.SOCK_STREAM)})
    except OSError as e:
        return 'gaierror'

def tls_fetch(sni, ca='/opt/test/ca.pem', host='127.0.0.1'):
    ctx = ssl.create_default_context(cafile=ca)
    s = socket.create_connection((host, 443), 5)
    t = ctx.wrap_socket(s, server_hostname=sni)
    t.sendall(b'GET /v1/models HTTP/1.1\r\nHost: api.neuralwatt.com\r\n\r\n')
    out = b''
    while True:
        d = t.recv(4096)
        if not d: break
        out += d
    return out.decode().partition('\r\n\r\n')[2]

def probe_tailnet(port):
    ip = os.environ.get('TAILNET_IP')  # the host's own tailnet address, passed by the runner at run time
    return attempt(lambda: tcp(ip, port)) if ip and port else 'unset'

mode = sys.argv[1]
if mode == 'isolation':
    r = {
        'host_loopback_canary': attempt(lambda: tcp('127.0.0.1', int(os.environ['CANARY_PORT']))),
        'tailnet_canary': probe_tailnet(int(os.environ.get('TAILNET_CANARY_PORT', '0'))),
        'tailnet_22': probe_tailnet(22),
        'tailnet_3003': probe_tailnet(3003),
        'lan_gateway_80': attempt(lambda: tcp('192.168.1.1', 80)),
        'public_v4_443': attempt(lambda: tcp('104.18.6.80', 443)),
        'public_v6_443': attempt(lambda: tcp('2606:4700:20::681a:650', 443, socket.AF_INET6)),
        'dns_udp_resolver': attempt(lambda: udp('1.1.1.1', 53)),
        'host_abstract_socket': attempt(lambda: abstract(os.environ['ABSTRACT_NAME'])),
        'other_unix_path': attempt(lambda: path_sock('/run/fca-egress/not-the-relay.sock')),
        'resolve_example_com': resolve('example.com'),
        'resolve_provider': resolve('api.neuralwatt.com'),
        'resolve_provider_alt': resolve('api.neuralwatt.com.evil.test'),
        'visible_mounts_run': sorted(os.listdir('/run')),
        'home_visible': os.path.exists('/home'),
    }
    print(json.dumps(r, sort_keys=True))
elif mode == 'caps':
    st = dict(l.split(':\t', 1) for l in open('/proc/self/status').read().splitlines() if ':\t' in l)
    shim_parent = open('/proc/%d/status' % os.getppid()).read()
    print(json.dumps({'uid': os.getuid(), 'gid': os.getgid(), 'groups': sorted(os.getgroups()), 'CapEff': st['CapEff'], 'CapPrm': st['CapPrm'],
                      'CapInh': st['CapInh'], 'CapAmb': st['CapAmb'], 'NoNewPrivs': st['NoNewPrivs'],
                      'listening_443': attempt(lambda: tcp('127.0.0.1', 443))}, sort_keys=True))
elif mode == 'positive':
    print(json.dumps({'response': tls_fetch('api.neuralwatt.com')[:8]}))
elif mode == 'negative':
    r = {}
    def wrong(sni):
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        s = socket.create_connection(('127.0.0.1', 443), 5)
        try:
            ctx.wrap_socket(s, server_hostname=sni)
            return 'HANDSHAKE-COMPLETED'
        except (OSError, ssl.SSLError) as e:
            return 'closed'
    r['wrong_sni'] = wrong('evil.example.test')
    r['lookalike_sni'] = wrong('api.neuralwatt.com.evil.test')
    r['ip_literal_sni'] = wrong('203.0.113.9')
    def plain(data):
        s = socket.create_connection(('127.0.0.1', 443), 5); s.settimeout(3)
        try:
            s.sendall(data); return 'closed' if s.recv(1) == b'' else 'GOT-DATA'
        except OSError:
            return 'closed'
    r['connect_request'] = plain(b'CONNECT evil.test:443 HTTP/1.1\r\nHost: evil.test\r\n\r\n')
    r['garbage'] = plain(os.urandom(200))
    print(json.dumps(r, sort_keys=True))
elif mode == 'node-truncation':
    js = r'''
const https = require('https'), fs = require('fs');
const ca = fs.readFileSync('/opt/test/ca.pem');
function go(path, label) { return new Promise(res => {
  let got = 0, err = '';
  const rq = https.request({host:'api.neuralwatt.com', path, method:'GET', timeout:5000, ca}, r => {
    r.on('data', d => got += d.length); r.on('error', e => { err = e.code || e.message; });
    r.on('close', () => res(label + ':' + (r.complete ? 'COMPLETE' : 'INCOMPLETE') + ':bytes=' + got + (err ? ':err=' + err : ''))); });
  rq.on('error', e => res(label + ':REQUEST-ERR:' + (e.code || e.message))); rq.on('timeout', () => rq.destroy()); rq.end(); }); }
(async () => {
  for (const [p, l] of [['/trunc-cl-fin','content-length-fin'], ['/trunc-cl-notify','content-length-notify'], ['/trunc-chunked-fin','chunked-fin'],
                        ['/delimited-fin','close-delimited-fin'], ['/delimited-notify','close-delimited-notify']]) console.log(await go(p, l));
})();
'''
    print(subprocess.run(['/opt/node/bin/node', '-e', js], capture_output=True, text=True, timeout=60).stdout.strip())
elif mode == 'node-positive':
    js = r'''
const https = require('https'), fs = require('fs');
function go(opts, label) { return new Promise(res => {
  const rq = https.request(Object.assign({host:'api.neuralwatt.com', path:'/v1/models', method:'GET', timeout:5000}, opts), r => {
    let b=''; r.on('data', d => b+=d); r.on('end', () => res(label+':'+b.slice(0,8))); });
  rq.on('error', e => res(label+':ERR:'+(e.code||e.message))); rq.on('timeout', () => { rq.destroy(); }); rq.end(); }); }
(async () => {
  console.log(await go({ca: fs.readFileSync('/opt/test/ca.pem')}, 'trusted-ca'));
  console.log(await go({}, 'default-roots'));
  console.log(await go({ca: fs.readFileSync('/opt/test/ca2.pem')}, 'unrelated-ca'));
})();
'''
    print(subprocess.run(['/opt/node/bin/node', '-e', js], capture_output=True, text=True, timeout=30).stdout.strip())
