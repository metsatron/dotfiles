#!/usr/bin/python3 -I
"""Runs the real relay under a distinct unprivileged uid with an injected resolver/connector (test fixture only; the production
entry point is fca_egress_relay.main). Usage: relay_runner.py MODULE_DIR SOCKET_DIR MOCK_PORT"""
import importlib.util, socket, sys
moddir, sockdir, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
spec = importlib.util.spec_from_file_location('fca_egress_relay', moddir + '/fca_egress_relay.py')
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
R._harden()
class Up:
    def __init__(self, s, a): self._s, self._a = s, a
    def getpeername(self): return (self._a, 443)
    def fileno(self): return self._s.fileno()
    def __getattr__(self, n): return getattr(self._s, n)
relay = R.Relay(sockdir + '/relay.sock', peer_uid=2012, resolver=lambda h, p: ['93.184.216.34'],
                connector=lambda a, p, t: Up(socket.create_connection(('127.0.0.1', port), t), a))
relay.bind()
print('relay-ready', flush=True)
relay.serve_forever()
