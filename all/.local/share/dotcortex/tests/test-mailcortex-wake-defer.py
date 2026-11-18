#!/usr/bin/env python3
"""Mail wake: a busy seat defers, it does not consume the mail.

The 18 Nov wedge: a transient refusal ("conditional idle authority unavailable" from a
live supervisor, or a busy seat) spent the receipt's attempt budget, and
requeue_with_attempts retired the mail as the terminal state `observed`. The scanner
never re-offers a terminal receipt, so every one of Fable's mails died while the seat
was merely busy, and the lane sat behind a single unturnable delivery.

These tests pin the two halves of the fix:
  * ClaudeLocalAdapter.resolve_idle_pane defers on a transient status instead of raising;
  * requeue_with_attempts defers instead of retiring when the exhausted reason is
    transient, and still retires a reason that will never clear.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[5]
WATCHER = ROOT / "all/.local/bin/mailcortex-seat-watcher"


def load_module(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class FakeWake:
    """Echo the request back the way the supervisor does, with a chosen status."""

    def __init__(self, status: str, owner: dict | None = None):
        self.status = status
        self.owner = owner if owner is not None else {"channel": "claude-x", "session_id": "s",
                                                      "supervisor_pid": 1, "supervisor_start_time": "1",
                                                      "epoch": 0, "pane_id": "%22", "pane_tty": "/dev/pts/1"}
        self.requests = []

    def remote_request(self, request):
        self.requests.append(request)
        reply = {"protocol": request["protocol"], "request_id": request["request_id"],
                 "target": request["target"], "status": self.status}
        if self.status == "idle":
            reply["owner"] = self.owner
        return reply

    def valid_owner(self, owner):
        return owner == self.owner


RECORD = {"claude_target": {"tmux_socket": "/tmp/tmux-1000/default", "tmux_session": "Fable",
                            "runtime_dir": "/run/user/1000"}}


class ResolveIdlePaneDefersTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module(WATCHER, "seat_watcher_defer_adapter")

    def _adapter_with(self, wake):
        adapter = self.module.ClaudeLocalAdapter()
        with mock.patch.object(self.module, "claude_wake", return_value=wake):
            return adapter

    def test_unavailable_status_defers_instead_of_raising(self):
        wake = FakeWake("unavailable")
        adapter = self._adapter_with(wake)
        with mock.patch.object(self.module, "claude_wake", return_value=wake):
            self.assertIsNone(adapter.resolve_idle_pane(RECORD))

    def test_unknown_and_invalid_status_defer(self):
        for status in ("unknown", "invalid"):
            wake = FakeWake(status)
            adapter = self._adapter_with(wake)
            with mock.patch.object(self.module, "claude_wake", return_value=wake):
                self.assertIsNone(adapter.resolve_idle_pane(RECORD))

    def test_busy_status_still_defers(self):
        wake = FakeWake("busy")
        adapter = self._adapter_with(wake)
        with mock.patch.object(self.module, "claude_wake", return_value=wake):
            self.assertIsNone(adapter.resolve_idle_pane(RECORD))

    def test_idle_with_valid_owner_returns_the_owner(self):
        wake = FakeWake("idle")
        adapter = self._adapter_with(wake)
        with mock.patch.object(self.module, "claude_wake", return_value=wake):
            self.assertEqual(adapter.resolve_idle_pane(RECORD), wake.owner)

    def test_idle_with_mismatched_owner_defers(self):
        wake = FakeWake("idle")
        wake.valid_owner = lambda owner: False
        adapter = self._adapter_with(wake)
        with mock.patch.object(self.module, "claude_wake", return_value=wake):
            self.assertIsNone(adapter.resolve_idle_pane(RECORD))


class RequeueDefersInsteadOfRetiringTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module(WATCHER, "seat_watcher_defer_requeue")
        self.writes = []

    def _requeue(self, reason, old, now=1_000.0):
        def capture(seat, mid, state, **extra):
            self.writes.append((seat, mid, state, extra))
        with mock.patch.object(self.module.MAILCORTEX, "write_wake_receipt", capture):
            return self.module.requeue_with_attempts("fable", "mid", reason, old, now)

    def test_exhausted_busy_defers_and_keeps_the_mail(self):
        spent = {"wake_attempts": self.module.REQUEUE_MAX_ATTEMPTS}
        self._requeue("busy", spent)
        seat, mid, state, extra = self.writes[-1]
        self.assertEqual(state, "queued", "a busy seat must not consume the mail")
        self.assertEqual(extra["reason"], "busy_deferred")
        self.assertEqual(extra["wake_attempts"], 0)
        self.assertEqual(extra["wake_defer_until"], 1_000.0 + self.module.DEFERRED_RETRY_SECONDS)
        self.assertEqual(extra["defer_cycles"], 1)

    def test_defer_cycles_accumulate(self):
        spent = {"wake_attempts": self.module.REQUEUE_MAX_ATTEMPTS, "defer_cycles": 3}
        self._requeue("transport_unavailable", spent)
        self.assertEqual(self.writes[-1][3]["defer_cycles"], 4)

    def test_transient_defer_keeps_cycling_rather_than_retiring(self):
        spent = {"wake_attempts": self.module.REQUEUE_MAX_ATTEMPTS}
        for _ in range(20):
            self._requeue("rate_limited", spent)
            spent = dict(spent, wake_attempts=self.module.REQUEUE_MAX_ATTEMPTS)
        self.assertTrue(all(write[2] == "queued" for write in self.writes),
                        "no transient refusal may ever write the terminal observed state")

    def test_permanent_reason_still_retires(self):
        spent = {"wake_attempts": self.module.REQUEUE_MAX_ATTEMPTS}
        self._requeue("policy_denied", spent)
        self.assertEqual(self.writes[-1][2], "observed")
        self.assertEqual(self.writes[-1][3]["reason"], "policy_denied_attempts_exhausted")


if __name__ == "__main__":
    unittest.main()
