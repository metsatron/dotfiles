#!/usr/bin/env python3
"""Black-box tests for the claude-warm PTY supervisor."""

from __future__ import annotations

import ast
import contextlib
import io
import json
import fcntl
import importlib.machinery
import importlib.util
import os
import pty
import pathlib
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
from unittest import mock


HERE = pathlib.Path(__file__).resolve()
REPO = HERE.parents[5]
WARM = REPO / "all/.local/bin/claude-warm"
OBSERVER = REPO / "all/.local/bin/claude-warm-live-observe"
HOOK = REPO / "all/.local/bin/claude-hook-idle-event"
STATUSLINE = REPO / "all/.local/bin/claude-statusline"


FAKE_CLAUDE = r'''#!/usr/bin/env python3
import fcntl
import os
import select
import signal
import struct
import subprocess
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
    if "--emit-terminal-modes" in sys.argv:
        os.write(1, b"\x1b[?1000h\x1b[?1004h\x1b[?1049h")
    signal.signal(signal.SIGWINCH, report_size)
    channel_child = None
    if "--spawn-channel-process" in sys.argv:
        channel_child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)", "server.ts"]
        )
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
            if b"/compact" in data:
                os.write(1, b"COMPACT_RECEIVED\n")
    finally:
        if channel_child is not None and channel_child.poll() is None:
            channel_child.terminate()
            channel_child.wait()


raise SystemExit(main())
'''


# Captured Kikin metadata shape for the delayed 2026-08-04 production record.
# Content and all identifiers are deliberately redacted; the classifier only
# needs the public record type/subtype and lifecycle metadata shape.
AWAY_SUMMARY_FIXTURE = {
    "content": "<redacted>",
    "cwd": "<redacted>",
    "entrypoint": "cli",
    "gitBranch": "<redacted>",
    "isMeta": False,
    "isSidechain": False,
    "parentUuid": "<redacted>",
    "sessionId": "<redacted>",
    "slug": "<redacted>",
    "subtype": "away_summary",
    "timestamp": "2026-08-04T03:11:40.142Z",
    "type": "system",
    "userType": "external",
    "uuid": "<redacted>",
    "version": "2.1.220",
}


def wait_until(predicate, timeout=5.0, message="condition did not become true"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError(message)


class Session:
    """One supervised fake Claude process and its private runtime directory."""

    def __init__(
        self,
        delay=10,
        ttl=60,
        extra_args=(),
        terminal=False,
        channel=False,
        attach_wait=30,
        recovery_cooldown=0,
        recovery_confirm=1,
        spawn_channel=False,
        retry=300,
        compact_timeout=900,
    ):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="cw", dir="/tmp"))
        self.fake = self.root / "fake-claude"
        self.fake.write_text(FAKE_CLAUDE, encoding="utf-8")
        self.fake.chmod(0o700)
        self.transcript = self.root / "transcript.jsonl"
        self.transcript.write_text("", encoding="utf-8")
        environment = os.environ.copy()
        environment.update(
            {
                "XDG_RUNTIME_DIR": str(self.root),
                "CLAUDE_IDLE_REAL_EXECUTABLE": str(self.fake),
                "CLAUDE_IDLE_COMPACT_SECONDS": str(delay),
                "CLAUDE_IDLE_COMPACT_LONG_CACHE_TTL_SECONDS": str(ttl),
                "CLAUDE_IDLE_COMPACT_STATUS_STOP_SKEW_SECONDS": "2",
                "CLAUDE_IDLE_COMPACT_TRANSCRIPT_QUIESCENCE_SECONDS": "0.1",
                "CLAUDE_IDLE_COMPACT_TRANSCRIPT_POLL_SECONDS": "1",
                "CLAUDE_IDLE_CACHE_PROFILE": "long",
                "CLAUDE_IDLE_COMPACTION_DEBUG": "1",
                "XDG_STATE_HOME": str(self.root / "state"),
                "CLAUDE_IDLE_CHANNEL_ATTACH_WAIT_SECONDS": str(attach_wait),
                "CLAUDE_IDLE_CHANNEL_RECOVERY_COOLDOWN_SECONDS": str(recovery_cooldown),
                "CLAUDE_IDLE_CHANNEL_RECOVERY_CONFIRM_SECONDS": str(recovery_confirm),
                "CLAUDE_IDLE_COMPACT_RETRY_SECONDS": str(retry),
                "CLAUDE_IDLE_COMPACT_TIMEOUT_SECONDS": str(compact_timeout),
            }
        )
        if channel:
            extra_args = ("--channels", "plugin:fixture@fixture", *extra_args)
            if spawn_channel:
                extra_args = (*extra_args, "--spawn-channel-process")
        self.parent_master = None
        self.outer_tty_fd = None
        self.outer_tty_baseline = None
        self.outer_tty_after = None
        if terminal:
            self.parent_master, parent_slave = pty.openpty()
            self.outer_tty_fd = os.dup(parent_slave)
            self.outer_tty_baseline = termios.tcgetattr(self.outer_tty_fd)
            self.process = subprocess.Popen(
                [str(WARM), *extra_args],
                stdin=parent_slave,
                stdout=parent_slave,
                stderr=parent_slave,
                env=environment,
            )
            os.close(parent_slave)
            self.output_fd = self.parent_master
        else:
            self.process = subprocess.Popen(
                [str(WARM), *extra_args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=environment,
            )
            assert self.process.stdout is not None
            self.output_fd = self.process.stdout.fileno()
        os.set_blocking(self.output_fd, False)
        self.output = bytearray()
        self.state_path = wait_until(self._find_state, message="state file missing")
        self.channel = self.state_path.parent.name
        self.socket_path = self.state_path.parent / "control.sock"
        self.session_id = "fixture-session"

    def _find_state(self):
        paths = list((self.root / "claude-idle-compaction").glob("claude-*/state.json"))
        return paths[0] if paths else None

    def read_state(self):
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def guard_events(self):
        path = self.root / "state" / "claude-idle-compaction" / f"{self.channel}.channel-guard.log"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        events = []
        for line in lines:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def output_contains(self, needle):
        if isinstance(needle, str):
            needle = needle.encode()
        while True:
            ready, _, _ = select.select([self.output_fd], [], [], 0)
            if not ready:
                break
            data = os.read(self.output_fd, 65536)
            if not data:
                break
            self.output.extend(data)
        return needle in self.output

    def wait_output(self, needle, timeout=5):
        try:
            wait_until(lambda: self.output_contains(needle), timeout, f"missing output {needle!r}")
        except AssertionError as error:
            raise AssertionError(
                f"{error}; state={self.read_state()!r}; output={bytes(self.output)!r}"
            ) from error

    def ipc(self, message):
        message = dict(message)
        message.setdefault("kind", "event")
        message.setdefault("channel", self.channel)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            connection.connect(str(self.socket_path))
            connection.sendall((json.dumps(message) + "\n").encode())
            return json.loads(connection.recv(65536).decode())

    def event(self, event, **fields):
        message = {"event": event, "session_id": self.session_id, **fields}
        return self.ipc(message)

    def status(self, tokens=80000, session_id=None, timestamp=None):
        payload = {
            "channel": self.channel,
            "session_id": session_id or self.session_id,
            "current_input_context_tokens": tokens,
            "update_timestamp": timestamp if timestamp is not None else time.time(),
        }
        path = self.state_path.parent / "status.json"
        temporary = path.with_name(".status-test.tmp")
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        temporary.replace(path)

    def append_transcript(self, entry):
        with self.transcript.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry) + "\n")

    def control(self, command, **fields):
        return self.ipc({"kind": "control", "command": command, **fields})

    def submit_local_byte(self, data=b"x"):
        if self.parent_master is not None:
            os.write(self.parent_master, data)
        else:
            assert self.process.stdin is not None
            self.process.stdin.write(data)
            self.process.stdin.flush()

    def set_size(self, rows, columns):
        assert self.parent_master is not None
        fcntl.ioctl(self.parent_master, termios.TIOCSWINSZ,
                    struct.pack("HHHH", rows, columns, 0, 0))

    def stop_and_bind(self, wait_quiescence=True):
        self.event("session-start", transcript_path=str(self.transcript))
        self.status()
        self.event("stop", stop_hook_active=False)
        if wait_quiescence:
            wait_until(
                lambda: self.read_state()
                and self.read_state().get("transcript_quiescence_deadline") is None,
                message="transcript quiescence was not established",
            )

    def close(self):
        if self.process.poll() is None:
            try:
                self.event("session-end")
            except (OSError, ConnectionError, json.JSONDecodeError):
                pass
            if self.process.stdin is not None:
                try:
                    self.process.stdin.close()
                except OSError:
                    pass
            elif self.parent_master is not None:
                self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.send_signal(signal.SIGTERM)
                self.process.wait(timeout=5)
        if self.process.stdin is not None:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        if self.process.stdout is not None:
            self.process.stdout.close()
        if self.parent_master is not None:
            self.output_contains(b"")
            try:
                self.outer_tty_after = termios.tcgetattr(self.outer_tty_fd)
            except OSError:
                self.outer_tty_after = None
            os.close(self.parent_master)
            self.parent_master = None
        if self.outer_tty_fd is not None:
            os.close(self.outer_tty_fd)
            self.outer_tty_fd = None
        shutil.rmtree(self.root, ignore_errors=True)


class ClaudeWarmTests(unittest.TestCase):
    def setUp(self):
        self.sessions = []
        loader = importlib.machinery.SourceFileLoader("claude_warm_test_module", str(WARM))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.module = importlib.util.module_from_spec(spec)
        loader.exec_module(self.module)

    def tearDown(self):
        for session in reversed(self.sessions):
            session.close()

    def make_session(self, **kwargs):
        session = Session(**kwargs)
        self.sessions.append(session)
        return session

    def test_herdr_registration_uses_supported_pane_contract(self):
        """The PTY owner reports logical identity and releases it cleanly."""
        root = pathlib.Path(tempfile.mkdtemp(prefix="cw-herdr-", dir="/tmp"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        socket_path = root / "herdr.sock"
        requests = []
        stop = threading.Event()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        server.listen(8)
        server.setblocking(False)

        def serve():
            while not stop.is_set():
                ready, _, _ = select.select([server], [], [], 0.05)
                if not ready:
                    continue
                try:
                    connection, _ = server.accept()
                except OSError:
                    if stop.is_set():
                        return
                    raise
                with connection:
                    payload = connection.recv(8192).splitlines()[0]
                    requests.append(json.loads(payload.decode("utf-8")))
                    connection.sendall(b'{"result":{}}\n')

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        self.addCleanup(stop.set)
        self.addCleanup(server.close)
        with mock.patch.dict(
            os.environ,
            {
                "HERDR_ENV": "1",
                "HERDR_SOCKET_PATH": str(socket_path),
                "HERDR_PANE_ID": "w4:pP",
                "CLAUDE_WARM_HERDR_AGENT": "Fable",
            },
            clear=False,
        ):
            reporter = self.module.HerdrReporter()
            reporter.child_pid = 12345
            reporter.register("fixture-session")
            reporter.report_state("working", "fixture-session")
            reporter.report_state("idle", "fixture-session")
            reporter.release()
        wait_until(lambda: len(requests) >= 7, message="Herdr requests were not received")
        methods = [request["method"] for request in requests]
        self.assertIn("pane.report_agent_session", methods)
        self.assertIn("pane.report_agent", methods)
        self.assertIn("pane.report_metadata", methods)
        self.assertEqual(methods[-1], "pane.release_agent")
        self.assertNotIn("pane.report_agent", methods[:2])
        for request in requests:
            params = request["params"]
            self.assertEqual(params["pane_id"], "w4:pP")
            self.assertEqual(params["source"], "claude-warm")
            self.assertEqual(params["agent"], "Fable")
        metadata = next(
            request["params"]
            for request in requests
            if request["method"] == "pane.report_metadata"
        )
        self.assertEqual(metadata["display_agent"], "Fable")
        self.assertEqual(metadata["tokens"]["claude_pid"], "12345")
        self.assertEqual(metadata["tokens"]["pty_owner"], "claude-warm")

    def test_herdr_identity_labels_are_preserved_by_all_wrappers(self):
        wrappers = {
            "Opus": pathlib.Path.home() / "HelmCortex/FORGE/bin/claude-opus",
            "Fable": pathlib.Path.home() / "HelmCortex/FORGE/bin/claude-fable",
            "Auryn": pathlib.Path.home() / "HelmCortex/FORGE/bin/claude-auryn",
        }
        for label, wrapper in wrappers.items():
            if not wrapper.is_file():
                self.skipTest(f"wrapper is not present: {wrapper}")
            source = wrapper.read_text(encoding="utf-8")
            self.assertIn(f"CLAUDE_WARM_HERDR_AGENT={label}", source)
            self.assertIn("claude-warm", source)

    def test_herdr_reporter_is_inert_outside_herdr(self):
        with mock.patch.dict(
            os.environ,
            {"HERDR_ENV": "0", "CLAUDE_WARM_HERDR_AGENT": "Fable"},
            clear=False,
        ):
            reporter = self.module.HerdrReporter()
            self.assertFalse(reporter.enabled)
            reporter.register("fixture-session")
            reporter.report_state("working", "fixture-session")
            reporter.release()

    def test_claude_screen_classifier_mirrors_visible_detector_evidence(self):
        classifier = self.module.ClaudeScreenClassifier()
        self.assertEqual(classifier.feed(b"\x1b]0;Claude Code\x07"), "unknown")
        self.assertEqual(classifier.feed("\x1b[2K  ❯\n".encode()), "idle")
        self.assertEqual(
            classifier.feed("✻ Working… (esc to interrupt)\n".encode()),
            "working",
        )
        self.assertEqual(
            classifier.feed(
                "Do you want to proceed?\n❯ 1. Yes\n  2. No\nEsc to cancel\n".encode()
            ),
            "blocked",
        )
        self.assertEqual(
            classifier.feed("\x1b[2K────────────────\n❯\n".encode()),
            "idle",
        )
        classifier.reset()
        self.assertEqual(
            classifier.feed("✻ Crunched for 16m 38s\n\n❯\n".encode()),
            "idle",
        )

    def test_arguments_and_full_pty_submission(self):
        session = self.make_session(delay=0, extra_args=("--resume", "fixture", "--model", "test"))
        session.wait_output("ARGS:['--resume', 'fixture', '--model', 'test']")
        session.stop_and_bind()
        session.wait_output("COMPACT_RECEIVED")
        self.assertEqual(session.read_state()["compacting"], True)
        session.event("post-compact")
        wait_until(lambda: session.read_state() and not session.read_state()["dirty"])
        self.assertEqual(
            bytes(session.output).count(b"INPUT:b'/compact\\n'"),
            1,
        )
        state = session.read_state()
        self.assertIsNone(state["timer_deadline"])
        self.assertEqual(state["last_injection_result"], "succeeded")
        self.assertEqual(state["last_state_transition"], "compaction-completed")

    def test_later_normal_turn_arms_a_fresh_timer(self):
        session = self.make_session(delay=1)
        session.stop_and_bind()
        session.wait_output("COMPACT_RECEIVED", timeout=3)
        session.event("post-compact")
        wait_until(lambda: session.read_state() and not session.read_state()["dirty"])
        session.status(tokens=80000)
        session.event("user-prompt-submit")
        session.event("stop", stop_hook_active=False)
        wait_until(
            lambda: session.read_state()
            and session.read_state()["timer_deadline"] is not None,
            message="later normal turn did not arm a fresh timer",
        )
        self.assertTrue(session.read_state()["dirty"])

    def test_foreign_project_session_start_does_not_rebind(self):
        # A nested one-shot claude inherits the supervisor's control-socket
        # env; its lifecycle hooks arrive here from another project directory
        # and must not steal the binding or end the governor (the 2026-08-20
        # overnight no-compact).  channel=True so the guard log exists: the
        # test only ever passed when it inherited CLAUDE_IDLE_WATCHED_SERVERS
        # from a supervised parent session.
        session = self.make_session(delay=30, channel=True)
        session.stop_and_bind()
        foreign_id = "one-shot-session"
        foreign_transcript = session.root / "foreign-project" / f"{foreign_id}.jsonl"
        response = session.event(
            "session-start",
            session_id=foreign_id,
            transcript_path=str(foreign_transcript),
        )
        self.assertEqual(response.get("ignored"), "foreign-session")
        self.assertEqual(session.read_state()["session_id"], session.session_id)
        response = session.event("session-end", session_id=foreign_id)
        self.assertEqual(response.get("error"), "session-mismatch")
        session.status(tokens=80000)
        session.event("user-prompt-submit")
        session.event("stop", stop_hook_active=False)
        wait_until(
            lambda: session.read_state()
            and session.read_state()["timer_deadline"] is not None,
            message="real session did not arm after a foreign session-start",
        )
        self.assertTrue(
            any(
                entry.get("event") == "foreign-session-ignored"
                for entry in session.guard_events()
            )
        )

    def test_rejected_compaction_clears_transient_flag_without_rearm(self):
        session = self.make_session(delay=0)
        session.stop_and_bind()
        session.wait_output("COMPACT_RECEIVED")
        self.assertTrue(session.read_state()["compacting"])
        session.append_transcript({
            "type": "system",
            "subtype": "local_command",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() + 1)),
            "content": "Not enough messages to compact.",
        })
        wait_until(
            lambda: session.read_state()
            and not session.read_state()["compacting"]
            and session.read_state()["last_cancellation_reason"] == "compaction-failed"
        )
        self.assertTrue(session.read_state()["dirty"])
        session.event("stop", stop_hook_active=False)
        time.sleep(0.2)
        self.assertIsNone(session.read_state()["timer_deadline"])
        self.assertEqual(bytes(session.output).count(b"COMPACT_RECEIVED"), 1)

    def test_stop_failure_clears_compacting_and_preserves_dirty(self):
        session = self.make_session(delay=0)
        session.stop_and_bind()
        session.wait_output("COMPACT_RECEIVED")
        session.event("stop-failure")
        wait_until(
            lambda: session.read_state()
            and not session.read_state()["compacting"]
            and session.read_state()["status"] == "error"
        )
        self.assertTrue(session.read_state()["dirty"])

    def test_resize_signal_reaches_child(self):
        session = self.make_session(terminal=True)
        session.wait_output("SIZE:")
        session.set_size(55, 123)
        session.process.send_signal(signal.SIGWINCH)
        # The supervisor owns the child PTY.  The changed size must reach the
        # fake child through its SIGWINCH handler.
        session.wait_output("SIZE:55x123")

    def test_local_keystroke_cancels(self):
        session = self.make_session(delay=1)
        session.stop_and_bind()
        session.submit_local_byte(b"draft")
        try:
            wait_until(lambda: session.read_state() and session.read_state()["last_cancellation_reason"] == "user-input")
        except AssertionError as error:
            raise AssertionError(f"{error}; state={session.read_state()!r}; output={bytes(session.output)!r}") from error
        time.sleep(1.3)
        self.assertFalse(session.output_contains("COMPACT_RECEIVED"))

    def test_terminal_protocol_traffic_does_not_cancel_timer(self):
        session = self.make_session(delay=2, terminal=True, channel=True)
        session.wait_output("ARGS:")
        session.wait_output("SIZE:")
        session.stop_and_bind()
        protocol = (
            b"\x1b[<35;10;20M",
            b"\x1b[<35;11;21m",
            b"\x1b[M" + bytes((35, 10, 20)),
            b"\x1b[I",
            b"\x1b[O",
            b"\x1b[12;34R",
            b"\x1b[6n",
            b"\x1b[?1;2c",
            b"\x1b[>0;95;0c",
            b"\x1b]10;rgb:ffff/ffff/ffff\x07",
        )
        for sequence in protocol:
            session.submit_local_byte(sequence)
        session.submit_local_byte(b"\x1b[<35;10;")
        session.submit_local_byte(b"20M")
        session.set_size(55, 123)
        session.process.send_signal(signal.SIGWINCH)
        wait_until(
            lambda: {
                kind
                for event in session.guard_events()
                if event.get("event") == "terminal-input"
                for kind in event.get("classifications", {})
            }
            >= {
                "sgr-mouse-report",
                "focus-report",
                "cursor-position-report",
                "device-status-report",
                "device-attribute-report",
            },
            message="terminal protocol bytes were not classified",
        )
        self.assertEqual(session.read_state().get("timer_kind"), "compact")
        self.assertNotEqual(session.read_state()["last_cancellation_reason"], "user-input")
        self.assertFalse(
            any(
                event.get("reason") == "user-input"
                for event in session.guard_events()
                if event.get("event") == "cancelled"
            )
        )
        terminal_events = [
            event for event in session.guard_events() if event.get("event") == "terminal-input"
        ]
        classifications = {
            kind
            for event in terminal_events
            for kind in event.get("classifications", {})
        }
        self.assertIn("sgr-mouse-report", classifications)
        self.assertIn("focus-report", classifications)
        self.assertIn("cursor-position-report", classifications)
        self.assertIn("device-status-report", classifications)
        self.assertIn("device-attribute-report", classifications)
        debug_path = pathlib.Path(session.read_state()["channel_debug_log"])
        self.assertNotIn("35;10;20", debug_path.read_text(encoding="utf-8"))
        self.assertNotIn(b"[claude-warm]", bytes(session.output))

    def test_bracketed_paste_framing_is_protocol_but_payload_cancels_once(self):
        session = self.make_session(delay=2, channel=True)
        session.stop_and_bind()
        session.submit_local_byte(b"\x1b[200")
        session.submit_local_byte(b"~")
        session.submit_local_byte(b"\x1b[201")
        session.submit_local_byte(b"~")
        wait_until(
            lambda: session.read_state()
            and session.read_state().get("timer_kind") == "compact",
            message="bracketed-paste framing cancelled the timer",
        )
        session.submit_local_byte(b"\x1b[200~pasted text\x1b[201~")
        wait_until(
            lambda: sum(
                event.get("reason") == "user-input"
                for event in session.guard_events()
                if event.get("event") == "cancelled"
            ) == 1,
            message="bracketed-paste payload did not cancel once",
        )
        session.submit_local_byte(b"more pasted text")
        time.sleep(0.1)
        self.assertEqual(
            sum(
                event.get("reason") == "user-input"
                for event in session.guard_events()
                if event.get("event") == "cancelled"
            ),
            1,
        )

    def test_keyboard_variants_cancel_once(self):
        keyboard_inputs = (
            b"x",
            "é".encode("utf-8"),
            b"\x7f",
            b"\r",
            b"\x1b",
            b"\x1b[A",
            b"\x1b[3~",
            b"\x1b[97;1u",
            b"\x1b[57361;1;9u",
        )
        for payload in keyboard_inputs:
            session = self.make_session(delay=30, channel=True)
            session.stop_and_bind()
            session.submit_local_byte(payload)
            wait_until(
                lambda: sum(
                    event.get("reason") == "user-input"
                    for event in session.guard_events()
                    if event.get("event") == "cancelled"
                ) == 1,
                message=f"keyboard input was not classified as human: {payload!r}",
            )
            session.submit_local_byte(payload)
            time.sleep(0.1)
            self.assertEqual(
                sum(
                    event.get("reason") == "user-input"
                    for event in session.guard_events()
                    if event.get("event") == "cancelled"
                ),
                1,
            )

    def test_claude_output_and_resize_do_not_count_as_input(self):
        session = self.make_session(
            delay=2,
            terminal=True,
            channel=True,
            extra_args=("--emit-terminal-modes",),
        )
        session.wait_output("ARGS:")
        session.stop_and_bind()
        session.set_size(48, 111)
        session.process.send_signal(signal.SIGWINCH)
        wait_until(
            lambda: session.read_state()
            and session.read_state().get("timer_kind") == "compact",
            message="Claude output or resize cancelled the timer",
        )
        self.assertNotIn(b"[claude-warm]", bytes(session.output))

    def test_terminal_state_is_restored_after_supervisor_exit(self):
        session = self.make_session(terminal=True, extra_args=("--emit-terminal-modes",))
        baseline = session.outer_tty_baseline
        session.wait_output("ARGS:")
        session.close()
        self.assertEqual(session.outer_tty_after, baseline)
        self.assertIn(b"\x1b[?1000l", bytes(session.output))
        self.assertIn(b"\x1b[?1004l", bytes(session.output))
        self.assertNotIn(b"\x1b[?1049l", bytes(session.output))

    def test_unicode_and_paste_bytes_proxy_through_pty(self):
        session = self.make_session(terminal=True)
        session.wait_output("ARGS:")
        session.submit_local_byte("héllo pasted\nsecond line\n".encode("utf-8"))
        first_chunk = b"INPUT:b'h\\xc3\\xa9llo pasted\\n'"
        second_chunk = b"INPUT:b'second line\\n'"
        wait_until(
            lambda: session.output_contains("")
            and first_chunk in bytes(session.output)
            and second_chunk in bytes(session.output),
            message="Unicode/paste bytes did not reach the fake PTY child",
        )

    def test_transcript_append_cancels(self):
        session = self.make_session(delay=1)
        session.stop_and_bind()
        # The production transcript is JSONL; a complete non-attachment entry
        # represents remote/channel activity without putting message content in
        # the supervisor log.
        session.append_transcript(
            {
                "type": "user",
                "timestamp": time.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() - 1)
                ),
            }
        )
        wait_until(lambda: session.read_state() and session.read_state()["last_cancellation_reason"] == "transcript-activity")
        self.assertFalse(session.output_contains("COMPACT_RECEIVED"))

    def test_delayed_away_summary_does_not_cancel_or_move_deadline(self):
        """The exact delayed recap record is not a new user/channel turn."""
        session = self.make_session(delay=3300, ttl=3600, channel=True)
        session.stop_and_bind()
        armed = session.read_state()
        deadline = armed["timer_deadline"]
        self.assertEqual(armed["timer_kind"], "compact")
        self.assertEqual(armed["cache_profile"], "long")
        self.assertAlmostEqual(
            deadline - armed["last_normal_stop"], 3300.0, places=2
        )
        simulated_delayed_record_at = armed["last_normal_stop"] + 185.644
        self.assertLess(simulated_delayed_record_at, deadline)
        session.append_transcript(AWAY_SUMMARY_FIXTURE)
        wait_until(
            lambda: session.read_state()
            and session.read_state()["last_transcript_classification"] == "internal-recap"
        )
        state = session.read_state()
        self.assertEqual(state["timer_kind"], "compact")
        self.assertAlmostEqual(state["timer_deadline"], deadline, places=3)
        self.assertFalse(state["transcript_gate_blocked"])
        self.assertEqual(
            len(
                [
                    event
                    for event in session.guard_events()
                    if event.get("event") == "armed" and event.get("kind") == "compact"
                ]
            ),
            1,
        )
        self.assertFalse(
            any(
                event.get("reason") == "transcript-activity"
                for event in session.guard_events()
                if event.get("event") == "cancelled"
            )
        )
        away_events = [
            event
            for event in session.guard_events()
            if event.get("event") == "transcript-record-ignored"
            and event.get("record_type") == "system"
            and event.get("record_subtype") == "away_summary"
        ]
        self.assertEqual(len(away_events), 1)
        self.assertEqual(away_events[0]["classification"], "internal-recap")

    def test_former_140_second_acceptance_predates_delayed_summary(self):
        """The old accelerated test fired before the observed +185.644s recap."""
        self.assertLess(140.0, 185.644)
        session = self.make_session(delay=0, ttl=300)
        session.stop_and_bind()
        session.wait_output("COMPACT_RECEIVED", timeout=3)
        self.assertEqual(bytes(session.output).count(b"INPUT:b'/compact\\n'"), 1)
        session.event("post-compact")
        wait_until(lambda: session.read_state() and not session.read_state()["dirty"])
        session.append_transcript(AWAY_SUMMARY_FIXTURE)
        time.sleep(0.2)
        self.assertEqual(bytes(session.output).count(b"INPUT:b'/compact\\n'"), 1)
        self.assertFalse(session.read_state()["compacting"])

    def test_internal_transcript_records_do_not_cancel_or_slide_deadline(self):
        session = self.make_session(delay=5)
        session.stop_and_bind()
        deadline = session.read_state()["timer_deadline"]
        records = [
            AWAY_SUMMARY_FIXTURE,
            {"type": "system", "subtype": "channel_send_failure"},
            {"type": "system", "subtype": "channel_send_retry"},
            {"type": "progress"},
            {"type": "status"},
            {"type": "queue-operation"},
            {"type": "file-history-snapshot"},
            {"type": "summary"},
            {"type": "user", "isMeta": True, "isSidechain": False},
            {"type": "assistant"},
        ]
        for record in records:
            session.append_transcript(record)
        wait_until(
            lambda: session.read_state()
            and session.read_state()["last_transcript_classification"] == "assistant-output"
        )
        state = session.read_state()
        self.assertEqual(state["timer_kind"], "compact")
        self.assertAlmostEqual(state["timer_deadline"], deadline, places=3)
        self.assertFalse(state["transcript_gate_blocked"])
        self.assertNotEqual(state["last_cancellation_reason"], "transcript-activity")

    def test_split_and_malformed_transcript_records_block_only_the_final_gate(self):
        session = self.make_session(delay=5)
        session.stop_and_bind()
        deadline = session.read_state()["timer_deadline"]
        encoded = json.dumps(AWAY_SUMMARY_FIXTURE).encode()
        with session.transcript.open("ab") as stream:
            stream.write(encoded[: len(encoded) // 2])
        time.sleep(0.2)
        state = session.read_state()
        self.assertIsNone(state["last_transcript_classification"])
        self.assertEqual(state["timer_deadline"], deadline)
        with session.transcript.open("ab") as stream:
            stream.write(encoded[len(encoded) // 2 :] + b"\n")
        wait_until(
            lambda: session.read_state()
            and session.read_state()["last_transcript_classification"] == "internal-recap"
        )
        with session.transcript.open("a", encoding="utf-8") as stream:
            stream.write("{malformed-json}\n[]\n")
        wait_until(
            lambda: session.read_state()
            and session.read_state()["transcript_gate_blocked"]
        )
        state = session.read_state()
        self.assertEqual(state["timer_deadline"], deadline)
        result = session.control("trigger")
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"]["last_gate_rejection_reason"], "transcript-uncertain")
        self.assertFalse(session.output_contains("COMPACT_RECEIVED"))

    def test_final_assistant_flush_does_not_cancel_idle_timer(self):
        session = self.make_session(delay=1)
        session.stop_and_bind(wait_quiescence=False)
        session.append_transcript(
            {
                "type": "assistant",
                "timestamp": time.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() + 1)
                ),
            }
        )
        wait_until(
            lambda: session.read_state()
            and session.read_state()["timer_deadline"] is not None,
            message="final assistant flush cancelled the timer",
        )
        self.assertNotEqual(session.read_state()["last_cancellation_reason"], "transcript-activity")
        session.wait_output("COMPACT_RECEIVED", timeout=3)

    def test_stop_bookkeeping_does_not_cancel_idle_timer(self):
        session = self.make_session(delay=1)
        session.stop_and_bind()
        session.append_transcript({"type": "system", "subtype": "stop_hook_summary"})
        session.append_transcript({"type": "system", "subtype": "turn_duration"})
        session.append_transcript({"type": "last-prompt"})
        session.append_transcript({"type": "mode"})
        session.append_transcript({"type": "permission-mode"})
        session.append_transcript({"type": "ai-title"})
        time.sleep(0.2)
        state = session.read_state()
        self.assertIsNotNone(state["timer_deadline"])
        self.assertNotEqual(state["last_cancellation_reason"], "transcript-activity")
        session.wait_output("COMPACT_RECEIVED", timeout=3)

    def test_new_user_record_cancels_even_with_coarse_timestamp(self):
        session = self.make_session(delay=1)
        session.stop_and_bind(wait_quiescence=False)
        session.append_transcript(
            {
                "type": "user",
                "channel": "telegram",
                "timestamp": time.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() - 1)
                ),
            }
        )
        wait_until(
            lambda: session.read_state()
            and session.read_state()["last_cancellation_reason"] == "transcript-activity"
        )
        self.assertFalse(session.output_contains("COMPACT_RECEIVED"))

    def test_channel_prompt_event_cancels(self):
        session = self.make_session(delay=1)
        session.stop_and_bind()
        session.event("user-prompt-submit")
        wait_until(lambda: session.read_state() and session.read_state()["last_cancellation_reason"] == "prompt-submit")
        time.sleep(1.3)
        self.assertFalse(session.output_contains("COMPACT_RECEIVED"))

    def test_snapshot_before_turn_and_session_mismatch_block(self):
        session = self.make_session(delay=30)
        session.stop_and_bind()
        session.status(timestamp=time.time() - 120)
        session.control("trigger")
        wait_until(lambda: session.read_state() and session.read_state()["last_cancellation_reason"] == "status-snapshot-before-stop")
        session.status(session_id="replacement-session")
        session.control("trigger")
        wait_until(lambda: session.read_state() and session.read_state()["last_cancellation_reason"] == "status-session-mismatch")

    def test_end_of_turn_snapshot_remains_valid_after_idle_delay(self):
        loader = importlib.machinery.SourceFileLoader("claude_warm_fixture", str(WARM))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        root = pathlib.Path(tempfile.mkdtemp(prefix="cw-snapshot", dir="/tmp"))
        try:
            snapshot = root / "status.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "channel": "claude-" + "a" * 32,
                        "session_id": "fixture-session",
                        "current_input_context_tokens": 210000,
                        "update_timestamp": 1000.5,
                    }
                ),
                encoding="utf-8",
            )
            supervisor = object.__new__(module.Supervisor)
            supervisor.snapshot_path = snapshot
            supervisor.channel = "claude-" + "a" * 32
            supervisor.session_id = "fixture-session"
            supervisor.last_normal_stop = 1000.0
            supervisor.completed_turn_epoch = 4
            supervisor.current_tokens = None
            supervisor.status_timestamp = None
            supervisor.status_snapshot_epoch = None
            with mock.patch.object(module, "now", return_value=4600.0):
                payload, error = supervisor._read_snapshot()
            self.assertIsNone(error)
            self.assertEqual(payload["current_input_context_tokens"], 210000)
            self.assertEqual(supervisor.status_snapshot_epoch, 4)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_production_defaults_and_resolver_rejects_wrapper(self):
        loader = importlib.machinery.SourceFileLoader("claude_warm_defaults", str(WARM))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.IDLE_SECONDS["long"], 55 * 60)
        self.assertEqual(module.TTL_SECONDS["long"], 60 * 60)
        self.assertEqual(module.MIN_TOKENS, 70000)
        root = pathlib.Path(tempfile.mkdtemp(prefix="cw-resolver", dir="/tmp"))
        try:
            with mock.patch.dict(
                os.environ,
                {"CLAUDE_IDLE_REAL_EXECUTABLE": str(WARM)},
                clear=False,
            ), mock.patch.object(module.shutil, "which", return_value=str(WARM)), mock.patch.object(
                module.pathlib.Path, "home", return_value=root
            ):
                with self.assertRaises(RuntimeError):
                    module.resolve_claude()
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_canonical_fable_telegram_launcher_delegates_to_supervisor(self):
        launcher = pathlib.Path(
            os.environ.get(
                "CLAUDE_IDLE_FABLE_LAUNCHER",
                str(pathlib.Path.home() / "HelmCortex/FORGE/bin/claude-fable"),
            )
        )
        if not launcher.is_file():
            self.skipTest("the machine-local Fable launcher is not present")
        source = launcher.read_text(encoding="utf-8")
        self.assertIn("Usage: claude-fable [--telegram]", source)
        self.assertIn("claude-warm --model", source)
        self.assertIn("--channels plugin:telegram@claude-plugins-official", source)

    def test_below_threshold_is_dormant_and_cold_cache_still_compacts(self):
        session = self.make_session(delay=30, ttl=1, channel=True)
        session.stop_and_bind()
        session.status(tokens=69999)
        session.control("trigger")
        wait_until(lambda: session.read_state() and session.read_state()["last_cancellation_reason"] == "below-token-threshold")
        self.assertEqual(session.read_state()["last_gate_rejection_reason"], "below-token-threshold")
        refusal = [
            event for event in session.guard_events()
            if event.get("event") == "gate-refused"
            and event.get("reason") == "below-token-threshold"
        ]
        self.assertEqual(len(refusal), 1)
        self.assertFalse(refusal[0]["transient"])
        self.assertEqual(session.read_state()["rearm_count"], 0)
        time.sleep(1.2)
        session.status(tokens=80000)
        # Ruling 2026-08-21: an expired warm-cache TTL no longer vetoes the
        # compaction; it is only recorded on the request.
        session.control("trigger")
        session.wait_output("COMPACT_RECEIVED")
        requested = [
            event for event in session.guard_events()
            if event.get("event") == "compaction-requested"
        ]
        self.assertEqual(len(requested), 1)
        self.assertEqual(requested[0]["cache"], "cold")
        self.assertFalse(requested[0]["queued_behind_turn"])

    def test_keystroke_rearms_and_compacts_after_idle_window(self):
        # The 2026-08-20 Opus overnight: one keystroke at 22:33 cancelled the
        # armed timer and nothing re-armed it until the morning.
        session = self.make_session(delay=1, retry=1, channel=True)
        session.stop_and_bind()
        session.submit_local_byte(b"x")
        wait_until(
            lambda: session.read_state()
            and session.read_state()["last_rearm_reason"] == "user-input"
            and session.read_state()["timer_deadline"] is not None,
            message="keystroke did not re-arm the timer",
        )
        self.assertEqual(session.read_state()["last_cancellation_reason"], "user-input")
        rearmed = [e for e in session.guard_events() if e.get("event") == "rearmed"]
        self.assertEqual(len(rearmed), 1)
        self.assertEqual(rearmed[0]["reason"], "user-input")
        # A second keystroke slides the window quietly: no second cancel/rearm.
        session.submit_local_byte(b"y")
        time.sleep(0.2)
        self.assertEqual(
            sum(1 for e in session.guard_events() if e.get("event") in {"rearmed", "cancelled"} and e.get("reason") == "user-input"),
            2,
        )
        session.wait_output("COMPACT_RECEIVED", timeout=4)
        requested = [e for e in session.guard_events() if e.get("event") == "compaction-requested"]
        self.assertEqual(requested[-1]["cache"], "warm")

    def test_live_turn_does_not_veto_after_idle_window(self):
        # The 2026-08-20 Fable overnight, generalized: activity cancels once,
        # re-arms, and a turn that never reaches Stop still gets its /compact
        # queued behind it once the idle window has passed.
        session = self.make_session(delay=1, retry=1, channel=True)
        session.stop_and_bind()
        session.event("session-activity")
        wait_until(
            lambda: session.read_state()
            and session.read_state()["status"] == "active"
            and session.read_state()["last_rearm_reason"] == "session-activity",
            message="mid-turn activity did not re-arm",
        )
        # Inside the idle window the gate still refuses, transiently.
        session.control("trigger")
        refusals = [
            e for e in session.guard_events()
            if e.get("event") == "gate-refused" and e.get("reason") == "session-active"
        ]
        self.assertEqual(len(refusals), 1)
        self.assertTrue(refusals[0]["transient"])
        self.assertIsNotNone(session.read_state()["timer_deadline"])
        session.wait_output("COMPACT_RECEIVED", timeout=4)
        requested = [e for e in session.guard_events() if e.get("event") == "compaction-requested"]
        self.assertTrue(requested[-1]["queued_behind_turn"])
        # The running turn's Stop is consumed as the compaction's Stop and
        # PostCompact closes the cycle as usual.
        session.event("stop", stop_hook_active=False)
        session.event("post-compact")
        wait_until(lambda: session.read_state() and not session.read_state()["dirty"])

    def test_transient_gate_refusal_rearms_but_dormant_does_not(self):
        session = self.make_session(delay=1, retry=1, channel=True)
        session.stop_and_bind()
        # Snapshot missing at fire time is transient: the timer re-arms.
        (session.state_path.parent / "status.json").unlink()
        wait_until(
            lambda: any(
                e.get("event") == "gate-refused" and e.get("reason") == "status-snapshot-missing"
                for e in session.guard_events()
            ),
            timeout=4,
        )
        wait_until(
            lambda: session.read_state()
            and session.read_state()["last_rearm_reason"] == "gate-refused:status-snapshot-missing"
            and session.read_state()["timer_deadline"] is not None,
            message="transient refusal did not re-arm",
        )
        session.status(tokens=80000)
        session.wait_output("COMPACT_RECEIVED", timeout=4)

    def test_compaction_timeout_clears_latch_and_rearms(self):
        session = self.make_session(delay=0, retry=1, compact_timeout=1, channel=True)
        session.stop_and_bind()
        session.wait_output("COMPACT_RECEIVED")
        self.assertTrue(session.read_state()["compacting"])
        wait_until(
            lambda: any(
                e.get("event") == "compaction-failed" and e.get("reason") == "timeout"
                for e in session.guard_events()
            ),
            timeout=4,
            message="lost compaction was not timed out",
        )
        wait_until(lambda: session.read_state() and not session.read_state()["compacting"])
        self.assertTrue(session.read_state()["dirty"])
        self.assertEqual(session.read_state()["last_rearm_reason"], "compaction-timeout")
        wait_until(
            lambda: session.output_contains(b"COMPACT_RECEIVED")
            and bytes(session.output).count(b"COMPACT_RECEIVED") >= 2,
            timeout=5,
            message="timed-out compaction was not retried",
        )
        # The retry's real Stop is not swallowed: PostCompact closes normally.
        session.event("post-compact")
        wait_until(lambda: session.read_state() and not session.read_state()["dirty"])

    def test_profile_change_rearms_with_new_delay(self):
        session = self.make_session(delay=30)
        session.stop_and_bind()
        before = session.read_state()["timer_deadline"]
        session.control("profile", profile="short")
        after = session.read_state()
        self.assertEqual(after["cache_profile"], "short")
        self.assertNotEqual(after["timer_deadline"], before)

    def test_hook_and_statusline_route_to_owner(self):
        session = self.make_session(delay=30)
        environment = os.environ.copy()
        environment.update(
            {
                "CLAUDE_IDLE_OWNER": "pty-supervisor",
                "CLAUDE_IDLE_CHANNEL": session.channel,
                "CLAUDE_IDLE_CONTROL_SOCKET": str(session.socket_path),
                "CLAUDE_IDLE_RUNTIME_DIR": str(session.state_path.parent),
            }
        )
        start = {
            "hook_event_name": "SessionStart",
            "session_id": session.session_id,
            "transcript_path": str(session.transcript),
        }
        subprocess.run(
            [str(HOOK)], input=json.dumps(start).encode(), env=environment,
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        status = {
            "session_id": session.session_id,
            "context_window": {"total_input_tokens": 80000},
        }
        subprocess.run(
            [str(STATUSLINE)], input=json.dumps(status).encode(), env=environment,
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        wait_until(lambda: session.read_state() and session.read_state()["session_id"] == session.session_id)
        snapshot = json.loads((session.state_path.parent / "status.json").read_text())
        self.assertEqual(snapshot["current_input_context_tokens"], 80000)
        stop = {
            "hook_event_name": "Stop",
            "session_id": session.session_id,
            "stop_hook_active": False,
            "last_assistant_message": "fixture completion",
        }
        subprocess.run(
            [str(HOOK)], input=json.dumps(stop).encode(), env=environment,
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        wait_until(lambda: session.read_state() and session.read_state()["dirty"])

    def test_statusline_registry_fallback_without_owner_environment(self):
        session = self.make_session(delay=30)
        session.event("session-start", transcript_path=str(session.transcript))
        environment = os.environ.copy()
        environment.update(
            {
                "XDG_RUNTIME_DIR": str(session.root),
                "CLAUDE_IDLE_OWNER": "",
                "CLAUDE_IDLE_CHANNEL": "",
                "CLAUDE_IDLE_RUNTIME_DIR": "",
            }
        )
        payload = {
            "session_id": session.session_id,
            "cwd": str(REPO),
            "model": {"display_name": "Claude Test"},
            "context_window": {"total_input_tokens": 81234},
        }
        subprocess.run(
            [str(STATUSLINE)], input=json.dumps(payload).encode(), env=environment,
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        snapshot_path = session.state_path.parent / "status.json"
        wait_until(lambda: snapshot_path.exists())
        snapshot = json.loads(snapshot_path.read_text())
        self.assertEqual(snapshot["channel"], session.channel)
        self.assertEqual(snapshot["session_id"], session.session_id)
        self.assertEqual(snapshot["current_input_context_tokens"], 81234)

    def test_two_sessions_are_isolated(self):
        first = self.make_session(delay=0)
        second = self.make_session(delay=30)
        self.assertNotEqual(first.channel, second.channel)
        first.stop_and_bind()
        first.wait_output("COMPACT_RECEIVED")
        self.assertFalse(second.read_state()["dirty"])
        second.stop_and_bind()
        second.submit_local_byte(b"x")
        time.sleep(0.2)
        self.assertFalse(second.output_contains("COMPACT_RECEIVED"))

    def test_channel_launch_attach_pass_and_fail(self):
        attached = self.make_session(
            channel=True,
            spawn_channel=True,
            attach_wait=2,
        )
        wait_until(
            lambda: attached.read_state() and attached.read_state()["channel_health"] == "attached",
            message="channel process was not recognized",
        )
        self.assertIn("plugin:fixture:fixture", attached.read_state()["watched_servers"])
        failed = self.make_session(channel=True, attach_wait=0)
        wait_until(
            lambda: failed.read_state() and failed.read_state()["channel_health"] == "failed-attach",
            message="missing channel process was not reported",
        )

    def test_channel_death_is_idempotent_and_bounded(self):
        session = self.make_session(
            channel=True,
            spawn_channel=True,
            attach_wait=2,
            recovery_confirm=1,
        )
        session.stop_and_bind()
        removed = {
            "type": "attachment",
            "attachment": {
                "type": "mcp_instructions_delta",
                "addedNames": [],
                "removedNames": ["plugin:fixture:fixture"],
            },
        }
        session.append_transcript(removed)
        session.append_transcript(removed)
        wait_until(
            lambda: session.read_state() and session.read_state()["channel_recovery_pending"],
            message="channel death did not create a recovery generation",
        )
        wait_until(
            lambda: session.read_state()
            and session.read_state()["channel_recovery_attempts"] >= 1
            and session.read_state()["channel_recovery_awaiting"],
            message="first reconnect was not injected",
        )
        session.wait_output("/mcp reconnect plugin:fixture:fixture", timeout=3)
        session.event("stop", stop_hook_active=False)
        wait_until(
            lambda: session.read_state()
            and session.read_state()["channel_recovery_attempts"] >= 2
            and session.read_state()["channel_recovery_awaiting"],
            message="second reconnect was not bounded/injected",
        )
        session.wait_output("/mcp reconnect plugin:fixture:fixture", timeout=3)
        session.event("stop", stop_hook_active=False)
        wait_until(
            lambda: session.read_state()
            and session.read_state()["channel_recovery_reload_attempted"]
            and session.read_state()["channel_recovery_awaiting"],
            message="reload fallback was not injected",
        )
        session.wait_output("/reload-plugins", timeout=3)
        session.event("stop", stop_hook_active=False)
        wait_until(
            lambda: session.read_state() and session.read_state()["channel_health"] == "dead",
            message="bounded recovery did not fail visibly",
            timeout=6,
        )
        # The fake child echoes the command once before each INPUT line. Count
        # the bytes received by the child, not the echoed terminal display.
        self.assertEqual(
            bytes(session.output).count(b"INPUT:b'/mcp reconnect plugin:fixture:fixture\\n'"),
            2,
        )
        self.assertEqual(bytes(session.output).count(b"INPUT:b'/reload-plugins\\n'"), 1)

    def test_channel_add_reemission_does_not_start_recovery(self):
        session = self.make_session(channel=True, spawn_channel=True, attach_wait=2)
        session.stop_and_bind()
        added = {
            "type": "attachment",
            "attachment": {
                "type": "mcp_instructions_delta",
                "addedNames": ["plugin:fixture:fixture"],
                "removedNames": [],
            },
        }
        session.append_transcript(added)
        session.append_transcript(added)
        wait_until(
            lambda: session.read_state() and session.read_state()["channel_health"] == "attached"
        )
        time.sleep(1.2)
        self.assertFalse(session.read_state()["channel_recovery_pending"])
        self.assertEqual(session.read_state()["timer_kind"], "compact")
        self.assertIsNotNone(session.read_state()["timer_deadline"])
        self.assertFalse(session.output_contains("/mcp reconnect"))

    def test_channel_recovery_confirmation_does_not_rearm_on_command_stop(self):
        session = self.make_session(
            channel=True,
            spawn_channel=True,
            attach_wait=2,
            recovery_confirm=2,
        )
        session.stop_and_bind()
        session.append_transcript({
            "type": "attachment",
            "attachment": {
                "type": "mcp_instructions_delta",
                "addedNames": [],
                "removedNames": ["plugin:fixture:fixture"],
            },
        })
        wait_until(
            lambda: session.read_state()
            and session.read_state()["channel_recovery_awaiting"]
        )
        session.append_transcript({
            "type": "attachment",
            "attachment": {
                "type": "mcp_instructions_delta",
                "addedNames": ["plugin:fixture:fixture"],
                "removedNames": [],
            },
        })
        wait_until(
            lambda: session.read_state()
            and session.read_state()["channel_health"] == "attached"
            and not session.read_state()["channel_recovery_pending"]
        )
        session.event("stop", stop_hook_active=False)
        time.sleep(0.2)
        self.assertIsNone(session.read_state()["timer_deadline"])

    def test_channel_death_waits_for_idle_and_prompt_cancels(self):
        session = self.make_session(channel=True, spawn_channel=True, attach_wait=2)
        session.event("session-start", transcript_path=str(session.transcript))
        session.append_transcript({
            "type": "attachment",
            "attachment": {
                "type": "mcp_instructions_delta",
                "addedNames": ["plugin:fixture:fixture"],
                "removedNames": [],
            },
        })
        session.event("user-prompt-submit")
        session.append_transcript({
            "type": "attachment",
            "attachment": {
                "type": "mcp_instructions_delta",
                "addedNames": [],
                "removedNames": ["plugin:fixture:fixture"],
            },
        })
        wait_until(lambda: session.read_state() and session.read_state()["channel_recovery_pending"])
        self.assertIsNone(session.read_state()["timer_deadline"])
        time.sleep(0.5)
        self.assertFalse(session.output_contains("/mcp reconnect"))
        session.event("user-prompt-submit")
        wait_until(lambda: session.read_state() and not session.read_state()["channel_recovery_pending"])
        self.assertFalse(session.output_contains("/mcp reconnect"))

    def test_channel_death_mid_turn_waits_for_stop(self):
        session = self.make_session(channel=True, spawn_channel=True, attach_wait=2)
        session.event("session-start", transcript_path=str(session.transcript))
        session.event("user-prompt-submit")
        session.append_transcript({
            "type": "attachment",
            "attachment": {
                "type": "mcp_instructions_delta",
                "addedNames": [],
                "removedNames": ["plugin:fixture:fixture"],
            },
        })
        wait_until(lambda: session.read_state() and session.read_state()["channel_recovery_pending"])
        time.sleep(0.5)
        self.assertFalse(session.output_contains("/mcp reconnect"))
        session.event("stop", stop_hook_active=False)
        wait_until(lambda: session.output_contains("/mcp reconnect plugin:fixture:fixture"))

    def test_inject_is_whitelist_only(self):
        session = self.make_session(delay=30)
        session.stop_and_bind()
        refused = session.control("inject", text="/bin/sh")
        self.assertFalse(refused["ok"])
        accepted = session.control("inject", text="/reload-plugins")
        self.assertTrue(accepted["ok"])
        session.wait_output("/reload-plugins")

    def test_exit_status_and_runtime_cleanup(self):
        session = self.make_session(extra_args=("--exit-status=7",))
        session.wait_output("ARGS:")
        session.process.wait(timeout=5)
        self.assertEqual(session.process.returncode, 7)
        runtime = session.root
        session.close()
        self.assertFalse(runtime.exists())

    def test_observation_harness_never_controls_an_interactive_supervisor(self):
        """The live acceptance observer must remain state/log read-only."""
        self.assertTrue(OBSERVER.is_file())
        source = OBSERVER.read_text(encoding="utf-8")
        tree = compile(source, str(OBSERVER), "exec", ast.PyCF_ONLY_AST)
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn("kill", calls)
        self.assertNotIn("send_signal", calls)
        self.assertNotIn("write", calls)
        self.assertNotIn('"inject"', source)
        self.assertNotIn('"trigger"', source)
        self.assertNotIn('"cancel"', source)
        self.assertNotIn("thread/compact/start", source)
        self.assertNotIn("SIGSTOP", source)
        self.assertNotIn("SIGCONT", source)

    def test_observation_harness_parses_list_shapes_and_snapshot_timestamps(self):
        loader = importlib.machinery.SourceFileLoader(
            "claude_warm_live_observe", str(OBSERVER)
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        channel = "claude-" + "a" * 32
        records = [{"channel": channel}, {"channel": "claude-" + "b" * 32}]
        self.assertEqual(module.parse_records(json.dumps(records)), records)
        self.assertEqual(module.parse_records("\n".join(json.dumps(item) for item in records)), records)
        self.assertEqual(module.timestamp_epoch(1700000000)[1], "integer")
        self.assertEqual(module.timestamp_epoch(1700000000.5)[1], "float")
        self.assertEqual(module.timestamp_epoch("1700000000.5")[1], "numeric-string")
        self.assertEqual(module.timestamp_epoch("2026-08-03T05:00:00Z")[1], "iso8601")

    def test_observer_success_report_accepts_an_aged_snapshot(self):
        """The completed-compaction report path keeps its regression bound defined."""
        loader = importlib.machinery.SourceFileLoader(
            "claude_warm_live_observe_success", str(OBSERVER)
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        channel = "claude-" + "c" * 32
        base = {
            "channel": channel,
            "supervisor_pid": 101,
            "pid": 102,
            "session_id": "observer-fixture-session",
            "cache_profile": "long",
            "watched_servers": [],
            "current_input_context_tokens": 80000,
            "dirty": True,
            "compacting": False,
            "timer_deadline": 240.0,
            "timer_kind": "compact",
            "last_injection_result": None,
        }
        armed = dict(base)
        completed = {
            **base,
            "dirty": False,
            "compacting": False,
            "timer_deadline": None,
            "timer_kind": None,
            "last_injection_result": "succeeded",
        }
        events = [
            {"event": "armed", "kind": "compact", "delay": 140, "timestamp": 100.0},
            {
                "event": "transcript-record-ignored",
                "classification": "internal-recap",
                "record_type": "system",
                "record_subtype": "away_summary",
                "timestamp": 185.644,
            },
            {"event": "injection-attempted", "purpose": "compact", "timestamp": 250.0},
            {"event": "compaction-requested", "timestamp": 250.0},
            {"event": "compaction-completed", "timestamp": 251.0},
        ]
        root = pathlib.Path(tempfile.mkdtemp(prefix="observer-success-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        guard = root / "guard.log"
        guard.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
        base["channel_guard_log"] = str(guard)
        states = iter([base, armed, completed, completed])
        sessions = iter([
            [{"channel": "claude-" + "d" * 32}],
            [{"channel": channel}],
        ])
        arguments = module.build_parser().parse_args([
            "--discovery-timeout", "1",
            "--arm-timeout", "1",
            "--compaction-timeout", "1",
            "--quiet-seconds", "0",
        ])
        self.assertEqual(arguments.former_snapshot_max_age, 120.0)
        with (
            mock.patch.object(module, "runtime_root", return_value=root),
            mock.patch.object(module, "control_command", return_value=root / "fake-warmctl"),
            mock.patch.object(module, "list_sessions", side_effect=lambda _command: next(sessions)),
            mock.patch.object(module, "read_state", side_effect=lambda _root, _channel: next(states)),
            mock.patch.object(module, "process_present", return_value=True),
            mock.patch.object(module, "supervisor_environment", return_value={
                "CLAUDE_IDLE_CACHE_PROFILE": "long",
                "CLAUDE_IDLE_COMPACT_SECONDS": "140",
                "CLAUDE_IDLE_COMPACT_LONG_CACHE_TTL_SECONDS": "300",
                "CLAUDE_IDLE_COMPACT_MIN_TOKENS": "1",
                "CLAUDE_IDLE_COMPACTION_DEBUG": "1",
            }),
            mock.patch.object(module, "read_status", return_value=(
                {"channel": channel, "session_id": "observer-fixture-session"},
                0.0,
                "integer",
                80000,
            )),
            mock.patch.object(module, "read_guard", return_value=events),
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = module.run(arguments)
        self.assertEqual(result, 0, output.getvalue())
        self.assertIn('result="PASS"', output.getvalue())
        self.assertIn('snapshot_age_at_callback_seconds=250.0', output.getvalue())
        self.assertIn('away_summary_observed=1', output.getvalue())
        self.assertIn('away_summary_classification="internal-recap"', output.getvalue())
        self.assertIn('away_summary_timer_preserved=true', output.getvalue())

    def test_signal_propagation_and_runtime_cleanup(self):
        session = self.make_session()
        session.wait_output("ARGS:")
        runtime = session.root
        session.process.send_signal(signal.SIGTERM)
        session.process.wait(timeout=5)
        self.assertEqual(session.process.returncode, 128 + signal.SIGTERM)
        session.close()
        self.assertFalse(runtime.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
