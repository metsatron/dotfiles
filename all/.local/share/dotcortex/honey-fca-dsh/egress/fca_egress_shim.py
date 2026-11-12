#!/usr/bin/python3 -I
"""Inside-namespace loopback shim for the sterile FCA DSH worker (SOURCE candidate; not provisioned).

Runs INSIDE the bwrap network namespace (which has no network but a loopback). It listens on 127.0.0.1:443, where /etc/hosts maps
api.neuralwatt.com, and copies opaque bytes to the one bound Unix socket of the host relay. It parses nothing and enforces nothing:
the relay is the enforcement point and the namespace stays offline. Usage: fca_egress_shim.py -- COMMAND [ARG...]; it binds the port
(the sandbox grants CAP_NET_BIND_SERVICE for exactly this), drops every capability, then runs COMMAND with the worker's environment.
Fail closed: if the relay socket is absent or the relay dies the client connection is closed at once. No fallback path exists."""
import ctypes
import os
import platform
import select
import socket
import subprocess
import sys
import threading
import time

LISTEN = ('127.0.0.1', 443)
RELAY_SOCKET = '/run/fca-egress/relay.sock'
MAX_CONCURRENT = 8
IDLE_DEADLINE = 60.0
TOTAL_DEADLINE = 900.0
CHUNK = 16384


class _CapData(ctypes.Structure):
    _fields_ = [('effective', ctypes.c_uint32), ('permitted', ctypes.c_uint32), ('inheritable', ctypes.c_uint32)]


def drop_all_capabilities():
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl(47, 4, 0, 0, 0)  # PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL
    header = (ctypes.c_uint32 * 2)(0x20080522, 0)  # _LINUX_CAPABILITY_VERSION_3, this thread
    data = (_CapData * 2)()
    nr = {'x86_64': 126, 'aarch64': 91}[platform.machine()]  # SYS_capset
    if libc.syscall(nr, ctypes.byref(header), ctypes.byref(data)) != 0:  # capset(zeroed sets)
        raise SystemExit('refused: could not drop capabilities')
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        raise SystemExit('refused: could not set no_new_privs')


def pump(a, b):
    start, open_ = time.monotonic(), {a, b}
    peer = {a: b, b: a}
    while open_:
        left = TOTAL_DEADLINE - (time.monotonic() - start)
        if left <= 0:
            return
        ready, _, _ = select.select(list(open_), [], [], min(IDLE_DEADLINE, left))
        if not ready:
            return
        for s in ready:
            try:
                s.settimeout(IDLE_DEADLINE)
                chunk = s.recv(CHUNK)
                if not chunk:
                    open_.discard(s)
                    peer[s].shutdown(socket.SHUT_WR)
                    continue
                peer[s].settimeout(IDLE_DEADLINE)
                peer[s].sendall(chunk)
            except (OSError, socket.timeout):
                return


def handle(client, slots):
    relay = None
    try:
        relay = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        relay.settimeout(5)
        relay.connect(RELAY_SOCKET)  # absent socket or dead relay: ENOENT/ECONNREFUSED, the client is closed below
        pump(client, relay)
    except OSError:
        pass
    finally:
        for s in (relay, client):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        slots.release()


def serve(listener):
    slots = threading.BoundedSemaphore(MAX_CONCURRENT)
    while True:
        try:
            client, _ = listener.accept()
        except OSError:
            return
        if not slots.acquire(blocking=False):
            client.close()
            continue
        threading.Thread(target=handle, args=(client, slots), daemon=True).start()


def main(argv):
    if len(argv) < 3 or argv[1] != '--':
        print('usage: fca_egress_shim.py -- COMMAND [ARG...]', file=sys.stderr)
        return 2
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(LISTEN)
    listener.listen(16)
    drop_all_capabilities()  # per-thread: done before any thread starts, so the accept thread and the child inherit none
    threading.Thread(target=serve, args=(listener,), daemon=True).start()
    return subprocess.run(argv[2:], check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
