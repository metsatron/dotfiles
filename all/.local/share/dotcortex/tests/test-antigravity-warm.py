#!/usr/bin/env python3
"""Black-box tests for the antigravity-warm PTY supervisor."""

from __future__ import annotations

import fcntl
import json
import os
import pathlib
import pty
import select
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import unittest


HERE = pathlib.Path(__file__).resolve()
REPO = HERE.parents[5]
WARM = REPO / "all/.local/bin/antigravity-warm"
HOOK = REPO / "all/.local/bin/antigravity-hook-idle-event"


FAKE_AGY = r'''#!/usr/bin/env python3
import fcntl
import os
import select
import signal
import struct
import sys
import termios


def report_size(_signum=None, _frame=None):
    try:
        raw = fcntl.ioctl(0, termios.TIOCGWINSZ, b"\0" * 8)
        rows, columns = struct.unpack("HH", raw[:4])
        os.write(1, (f"SIZE:{rows}x{columns}\n").encode())
    except OSError:
        pass


def main():
    os.write(1, (f"ARGS:{sys.argv[1:]!r}\n").encode())
    report_size()
    signal.signal(signal.SIGWINCH, report_size)
    if "--exit-status=7" in sys.argv:
        return 7
    try:
        while True:
            readable, _, _ = select.select([0], [], [], 0.1)
            if not readable:
                continue
            data = os.read(0, 65536)
            if not data:
                return 0
            os.write(1, (f"INPUT:{data!r}\n").encode())
    except KeyboardInterrupt:
        return 0


raise SystemExit(main())
'''


def wait_until(predicate, timeout=5.0, message="condition did not become true"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError(message)


class Session:
    """One supervised fake Antigravity process and its private runtime directory."""

    def __init__(self, extra_args=()):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="agyw", dir="/tmp"))
        self.fake = self.root / "fake-agy"
        self.fake.write_text(FAKE_AGY, encoding="utf-8")
        self.fake.chmod(0o700)
        self.env = os.environ.copy()
        self.env.update(
            {
                "XDG_RUNTIME_DIR": str(self.root),
                "XDG_STATE_HOME": str(self.root / "state"),
                "ANTIGRAVITY_IDLE_REAL_EXECUTABLE": str(self.fake),
                "ANTIGRAVITY_IDLE_COMPACTION_DEBUG": "1",
            }
        )
        self.process = subprocess.Popen(
            [str(WARM), *extra_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
        )
        self.socket_path = wait_until(
            self._find_socket, timeout=5.0, message="socket did not appear"
        )
        self.channel = self.socket_path.parent.name

    def _find_socket(self) -> pathlib.Path | None:
        sockets = list(self.root.glob("antigravity-idle-compaction/*/socket"))
        return sockets[0] if sockets else None

    def control(self, command: str, **kwargs) -> dict:
        payload = {"command": command, **kwargs}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2.0)
            client.connect(str(self.socket_path))
            client.sendall((json.dumps(payload) + "\n").encode())
            data = client.recv(65536)
            return json.loads(data.split(b"\n", 1)[0].decode("utf-8"))

    def send_event(self, event: str, session_id: str = "test-session") -> dict:
        payload = {
            "kind": "event",
            "event": event,
            "channel": self.channel,
            "session_id": session_id,
        }
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2.0)
            client.connect(str(self.socket_path))
            client.sendall((json.dumps(payload) + "\n").encode())
            data = client.recv(65536)
            return json.loads(data.split(b"\n", 1)[0].decode("utf-8"))

    def close(self):
        try:
            self.process.terminate()
            self.process.wait(timeout=2.0)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        shutil.rmtree(self.root, ignore_errors=True)


class TestAntigravityWarm(unittest.TestCase):
    def test_supervisor_lifecycle_and_ipc(self):
        session = Session(extra_args=["--custom-flag"])
        try:
            state = session.control("state")
            self.assertTrue(state.get("ok"))
            self.assertEqual(state["state"]["status"], "idle")
            self.assertTrue(state["state"]["channel"].startswith("antigravity-"))

            # Send lifecycle events
            ev_res = session.send_event("session-start", "test-session-123")
            self.assertTrue(ev_res.get("ok"))
            self.assertEqual(ev_res["state"]["session_id"], "test-session-123")

            ev_res = session.send_event("user-prompt-submit", "test-session-123")
            self.assertTrue(ev_res.get("ok"))
            self.assertEqual(ev_res["state"]["status"], "active")

            ev_res = session.send_event("stop", "test-session-123")
            self.assertTrue(ev_res.get("ok"))
            self.assertEqual(ev_res["state"]["status"], "idle")
            self.assertGreater(ev_res["state"]["rearm_count"], 0)

            # Test injection
            inj_res = session.control("inject", text="echo hello\n")
            self.assertTrue(inj_res.get("ok"))
        finally:
            session.close()

    def test_hook_idle_event(self):
        session = Session()
        try:
            hook_env = session.env.copy()
            hook_env.update(
                {
                    "ANTIGRAVITY_IDLE_CHANNEL": session.channel,
                    "ANTIGRAVITY_IDLE_OWNER": "pty-supervisor",
                    "ANTIGRAVITY_IDLE_CONTROL_SOCKET": str(session.socket_path),
                }
            )
            # Invoke hook with SessionStart JSON payload
            start_payload = json.dumps(
                {
                    "hookEventName": "SessionStart",
                    "conversationId": "conv-uuid-456",
                }
            )
            subprocess.run(
                [str(HOOK)],
                input=start_payload.encode(),
                env=hook_env,
                check=True,
                timeout=3,
            )

            state = session.control("state")
            self.assertEqual(state["state"]["session_id"], "conv-uuid-456")

            # Invoke hook with Stop payload
            stop_payload = json.dumps(
                {
                    "hookEventName": "Stop",
                    "conversationId": "conv-uuid-456",
                    "stop_hook_active": False,
                }
            )
            subprocess.run(
                [str(HOOK)],
                input=stop_payload.encode(),
                env=hook_env,
                check=True,
                timeout=3,
            )
            state2 = session.control("state")
            self.assertEqual(state2["state"]["status"], "idle")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
