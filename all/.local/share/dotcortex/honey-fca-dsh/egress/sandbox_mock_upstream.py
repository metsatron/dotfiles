#!/usr/bin/python3 -I
"""Synthetic TLS upstream for the sandbox integration test (test fixture only). Usage: sandbox_mock_upstream.py CERT KEY PORTFILE"""
import hashlib, socket, ssl, sys, threading
cert, key, portfile = sys.argv[1:4]
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(cert, key)
srv = socket.socket(); srv.bind(('127.0.0.1', 0)); srv.listen(16)
with open(portfile, 'w') as f:
    f.write(str(srv.getsockname()[1]))
def one(c):
    try:
        t = ctx.wrap_socket(c, server_side=True)
        buf = b''
        while b'\r\n\r\n' not in buf:
            d = t.recv(4096)
            if not d:
                return
            buf += d
        parts = buf.split(b'\r\n', 1)[0].split(b' ')
        path = parts[1] if len(parts) > 1 else b'/'
        # Truncation fixtures (test_06b). Every one reads the whole request first, so a close is a FIN and never a RST.
        if path.startswith(b'/trunc-') or path.startswith(b'/delimited-'):
            if path.startswith(b'/trunc-cl'):
                t.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 100\r\nConnection: close\r\n\r\npartial-body')
            elif path.startswith(b'/trunc-chunked'):
                t.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n5\r\nhello\r\n')
            else:
                t.sendall(b'HTTP/1.1 200 OK\r\nConnection: close\r\n\r\npartial-body')
            if path.endswith(b'-notify'):
                t.unwrap()  # orderly TLS shutdown: close_notify is sent
            t.close()  # otherwise: TCP FIN with no close_notify
            return
        body = b'mock-ok ' + hashlib.sha256(buf).hexdigest().encode()
        t.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\nContent-Length: %d\r\n\r\n' % len(body) + body)
        t.close()
    except (OSError, ssl.SSLError):
        pass
while True:
    c, _ = srv.accept()
    threading.Thread(target=one, args=(c,), daemon=True).start()
