#!/usr/bin/env python3
"""Deterministic fixture tests for the OpenCode watchdog turn-stall assist."""

from __future__ import annotations

import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest


HERE = Path(__file__).resolve()
WATCHDOG = HERE.parents[3] / "bin" / "opencode-watchdog"
SESSION_ID = "ses_fixture00000000000000000000000"
PROJECT = "/home/metsatron/HelmCortex"
HOST = Path("/etc/hostname").read_text(encoding="utf-8").strip()


def incomplete_turn() -> dict:
    return {
        "info": {"id": "msg_fixture", "role": "assistant", "time": {"created": 1}},
        "parts": [
            {"type": "text", "text": "working"},
            {"type": "tool", "tool": "read", "state": {
                "status": "running", "time": {"start": 1000},
                "input": {"filePath": "/x"},
            }},
        ],
    }


class Fixture:
    def __init__(self) -> None:
        self.status: object = {SESSION_ID: {"type": "busy"}}
        self.messages: object = [{"info": {"role": "user"}, "parts": []}, incomplete_turn()]
        self.aborts = 0
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def send_json(self, code: int, payload: object = None) -> None:
                body = b"" if payload is None else json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/":
                    self.send_json(200, {})
                elif self.path == "/session/status":
                    self.send_json(200, outer.status)
                elif self.path.startswith(f"/session/{SESSION_ID}/message"):
                    self.send_json(200, outer.messages)
                else:
                    self.send_json(404, {})

            def do_POST(self) -> None:  # noqa: N802
                if self.path == f"/session/{SESSION_ID}/abort":
                    outer.aborts += 1
                    self.send_json(200, {})
                else:
                    self.send_json(404, {})

            def log_message(self, *args: object) -> None:
                return

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class WatchdogTurnStallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="opencode-watchdog-")
        self.root = Path(self.temp.name)
        self.fixture = Fixture()
        self.addCleanup(self.fixture.close)
        self.owner = self.root / "owner"
        self.owner.write_text(
            "#!/usr/bin/env python3\n"
            "import json\n"
            "print(json.dumps({'status': 'running', 'reasons': [],\n"
            "                  'backend': {'pid': 1, 'valid': True},\n"
            "                  'poller': {'pid': 2, 'valid': True}}))\n",
            encoding="utf-8",
        )
        os.chmod(self.owner, 0o755)
        self.marker = self.root / "manager.calls"
        self.manager = self.root / "manager"
        self.manager.write_text(f"#!/bin/sh\necho \"$@\" >> {self.marker}\n", encoding="utf-8")
        os.chmod(self.manager, 0o755)
        self.owner_state = self.root / "opencode.json"
        self.owner_state.write_text(json.dumps({
            "schema": "helmcortex.opencode-owner.v2",
            "session_binding": {"status": "bound", "session_id": SESSION_ID},
        }), encoding="utf-8")
        self.state = self.root / "state.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_watchdog(self, *extra: str) -> dict:
        command = [
            str(WATCHDOG), "--expected-host", HOST, "--json",
            "--owner", str(self.owner), "--owner-state", str(self.owner_state),
            "--manager", str(self.manager), "--project", PROJECT,
            "--port", str(self.fixture.port), "--watchdog-state", str(self.state),
            "--api-timeout", "1.0", *extra,
        ]
        result = subprocess.run(command, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def read_state(self) -> dict:
        return json.loads(self.state.read_text(encoding="utf-8"))

    def test_progressing_turn_is_not_aborted(self) -> None:
        first = self.run_watchdog("--turn-stall-seconds", "0")
        self.assertEqual(first["status"], "healthy")
        self.assertEqual(first["turn"]["status"], "progress")
        second = self.run_watchdog("--turn-stall-seconds", "99999")
        self.assertEqual(second["turn"]["status"], "waiting")
        self.assertEqual(self.fixture.aborts, 0)

    def test_confirmed_stall_aborts_the_turn(self) -> None:
        self.run_watchdog("--turn-stall-seconds", "99999")
        event = self.run_watchdog("--turn-stall-seconds", "0")
        self.assertEqual(event["status"], "turn-stall-aborted")
        self.assertEqual(event["turn"]["abort_status"], 200)
        self.assertEqual(self.fixture.aborts, 1)

    def test_idle_session_clears_stall_state(self) -> None:
        self.state.write_text(json.dumps({
            "schema": "dotcortex.opencode-watchdog.v1",
            "stall_fingerprint": "deadbeef",
            "stall_since": time.time() - 5000,
        }), encoding="utf-8")
        self.fixture.status = {}
        event = self.run_watchdog()
        self.assertEqual(event["status"], "healthy")
        self.assertNotIn("stall_fingerprint", self.read_state())
        self.assertEqual(self.fixture.aborts, 0)

    def test_repeated_stalls_escalate_to_recovery_worker(self) -> None:
        self.run_watchdog("--turn-stall-seconds", "99999")
        state = self.read_state()
        state["stall_since"] = time.time() - 3600
        state["stall_aborts"] = [time.time() - 60]
        self.state.write_text(json.dumps(state), encoding="utf-8")
        event = self.run_watchdog("--turn-stall-seconds", "0")
        self.assertEqual(event["status"], "turn-stall-escalated")
        self.assertEqual(self.fixture.aborts, 1)
        deadline = time.time() + 15
        while time.time() < deadline and not self.marker.exists():
            time.sleep(0.1)
        self.assertTrue(self.marker.exists(), "recovery worker never invoked the manager")
        self.assertIn("stop opencode", self.marker.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
