#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
WATCHER = ROOT / "all/.local/bin/mailcortex-seat-watcher"


def load_module(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class FakeAdapter:
    def __init__(self, *, busy=False, fail=False):
        self.busy = busy
        self.fail = fail
        self.deliveries = []

    def resolve_idle_pane(self, record):
        return None if self.busy else "wT:p1"

    def deliver(self, record, pane_id, prompt):
        self.deliveries.append((record["herdr_target"], pane_id, prompt))
        if self.fail:
            raise RuntimeError("ambiguous transport failure")


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "Mail"
        self.runtime = self.base / "runtime"
        os.environ.update(MAILCORTEX_ROOT=str(self.root),
                          MAILCORTEX_RUNTIME=str(self.runtime),
                          MAILCORTEX_HOSTNAME="test-host")
        self.mailbox = self.root / "seats/builder"
        for leaf in ("tmp", "new", "cur"):
            (self.mailbox / leaf).mkdir(parents=True)
        self.watcher = load_module(WATCHER, "mailcortex_watcher_test")
        self.registry = {"schema": "mailcortex.seats.v1", "host": "test-host", "seats": {"builder": {
            "host": "test-host", "mailbox": "seats/builder", "harness": "codex",
            "transport": "herdr", "herdr_session": "builder-session",
            "herdr_target": "builder-agent", "rate_limit_seconds": 0,
        }}}

    def tearDown(self):
        self.temp.cleanup()

    def mail(self, mid, filename):
        message = EmailMessage()
        message["From"] = "sender@node.helm"
        message["To"] = "seat+builder@node.helm"
        message["Subject"] = "wake"
        message["Message-ID"] = mid
        message.set_content("hello")
        (self.mailbox / "new" / filename).write_bytes(message.as_bytes())

    def receipt(self, mid):
        return self.watcher.MAILCORTEX.load_receipt("builder", mid)

    def test_idle_injects_once_and_duplicate_filename_does_not_repeat(self):
        self.mail("<same@node.helm>", "a")
        self.mail("<same@node.helm>", "b")
        adapter = FakeAdapter()
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=10), 1)
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=11), 0)
        self.assertEqual(adapter.deliveries, [("builder-agent", "wT:p1", "/inbox")])
        self.assertEqual(self.receipt("<same@node.helm>")["wake_state"], "injected")

    def test_in_flight_sync_temp_file_is_not_a_wake(self):
        self.mail("<partial@node.helm>", ".syncthing.123.host.tmp")
        adapter = FakeAdapter()
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=10), 0)
        self.assertEqual(adapter.deliveries, [])

    def test_busy_and_rate_limit_defer_without_drop(self):
        self.mail("<busy@node.helm>", "a")
        adapter = FakeAdapter(busy=True)
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=10), 0)
        self.assertEqual(self.receipt("<busy@node.helm>")["wake_state"], "queued")
        adapter.busy = False
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=11), 1)
        self.registry["seats"]["builder"]["rate_limit_seconds"] = 30
        self.mail("<later@node.helm>", "b")
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=20), 0)
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=42), 1)

    def test_handling_state_preserves_wake_and_does_not_reinject(self):
        mid = "<deferred@node.helm>"
        self.mail(mid, "a")
        adapter = FakeAdapter()
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=10), 1)
        self.watcher.MAILCORTEX.write_handling_receipt("builder", mid, "handling_deferred")
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=11), 0)
        receipt = self.receipt(mid)
        self.assertEqual(receipt["wake_state"], "injected")
        self.assertEqual(receipt["handling_state"], "handling_deferred")
        self.assertEqual(len(adapter.deliveries), 1)

    def test_ambiguous_delivery_is_not_retried(self):
        mid = "<unknown@node.helm>"
        self.mail(mid, "a")
        adapter = FakeAdapter(fail=True)
        with self.assertRaisesRegex(self.watcher.WatcherError, "outcome is unknown"):
            self.watcher.locked_scan(self.registry, adapter, now=10)
        self.assertEqual(self.receipt(mid)["wake_state"], "delivery_unknown")
        adapter.fail = False
        self.assertEqual(self.watcher.locked_scan(self.registry, adapter, now=11), 0)
        self.assertEqual(len(adapter.deliveries), 1)

    def test_message_id_hash_has_no_sanitizing_collision(self):
        first = self.watcher.MAILCORTEX.receipt_path("builder", "<a+b@node.helm>")
        second = self.watcher.MAILCORTEX.receipt_path("builder", "<a/b@node.helm>")
        self.assertNotEqual(first, second)

    def test_malformed_mail_and_corrupt_receipt_fail_loud(self):
        (self.mailbox / "new/bad").write_text("not RFC 822")
        with self.assertRaisesRegex(self.watcher.WatcherError, "valid Message-ID"):
            self.watcher.locked_scan(self.registry, FakeAdapter())
        (self.mailbox / "new/bad").unlink()
        mid = "<bad-receipt@node.helm>"
        self.mail(mid, "good")
        path = self.watcher.MAILCORTEX.receipt_path("builder", mid)
        path.parent.mkdir(parents=True)
        path.write_text("{}")
        with self.assertRaisesRegex(self.watcher.WatcherError, "receipt is invalid"):
            self.watcher.locked_scan(self.registry, FakeAdapter())

    def test_registry_and_scan_lock_fail_closed(self):
        registry_path = self.base / "registry.json"
        registry_path.write_text(json.dumps(self.registry))
        registry_path.chmod(0o600)
        with self.assertRaises(self.watcher.WatcherError):
            self.watcher.load_registry(registry_path, "other-host")
        lock_path = self.runtime / "watcher.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(self.watcher.WatcherError, "owns the scan lock"):
                self.watcher.locked_scan(self.registry, FakeAdapter())

    def test_production_adapter_uses_verified_herdr_shape_and_commands(self):
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            if command[3:5] == ["agent", "get"]:
                payload = {"result": {"agent": {"name": "builder-agent",
                           "pane_id": "wT:p1", "agent_status": "idle"}}}
                return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
            if command[3:5] == ["pane", "run"]:
                return subprocess.CompletedProcess(command, 0, "{}", "")
            self.fail(f"unexpected Herdr command: {command}")

        record = self.registry["seats"]["builder"]
        adapter = self.watcher.HerdrAdapter(runner=runner)
        pane = adapter.resolve_idle_pane(record)
        self.assertEqual(pane, "wT:p1")
        adapter.deliver(record, pane, "/inbox")
        self.assertEqual(calls, [
            ["herdr", "--session", "builder-session", "agent", "get", "builder-agent"],
            ["herdr", "--session", "builder-session", "pane", "run", "wT:p1", "/inbox"],
        ])

    def test_production_adapter_accepts_done_but_not_unknown(self):
        states = iter(("done", "unknown"))

        def runner(command, **kwargs):
            payload = {"result": {"agent": {"name": "builder-agent",
                       "pane_id": "wT:p1", "agent_status": next(states)}}}
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

        record = self.registry["seats"]["builder"]
        adapter = self.watcher.HerdrAdapter(runner=runner)
        self.assertEqual(adapter.resolve_idle_pane(record), "wT:p1")
        self.assertIsNone(adapter.resolve_idle_pane(record))


if __name__ == "__main__":
    unittest.main()
