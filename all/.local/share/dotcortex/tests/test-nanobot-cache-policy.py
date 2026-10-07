"""Behavior checks for Nano's measured cache-expiry token gate."""
from __future__ import annotations

from datetime import datetime, timedelta
import os
import unittest
from unittest import mock

from nanobot.agent.autocompact import AutoCompact


class FakeSession:
    def __init__(self) -> None:
        self.key = "telegram:approved"
        self.updated_at = datetime.now() - timedelta(hours=3)
        self.messages = [{"role": "user", "content": "durable context"}]
        self.last_archived = 0
        self.metadata = {}


class FakeSessions:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def list_sessions(self):
        return [{"key": self.session.key, "updated_at": self.session.updated_at}]

    def get_or_create(self, _key: str):
        return self.session


class FakeConsolidator:
    def __init__(self, estimated_tokens: int) -> None:
        self.estimated_tokens = estimated_tokens

    def estimate_session_prompt_tokens(self, _session, *, runtime):
        return self.estimated_tokens, "fixture"


class NanoCachePolicyTest(unittest.TestCase):
    def run_scan(self, estimated_tokens: int) -> int:
        session = FakeSession()
        compact = AutoCompact(FakeSessions(session), FakeConsolidator(estimated_tokens))
        scheduled = []
        runtime = object()
        with mock.patch.object(AutoCompact, "_policy_ttl_seconds", return_value=60), \
             mock.patch.dict(os.environ, {"NANOBOT_CACHE_POLICY_MIN_TOKENS": "70000"}):
            compact.check_expired(scheduled.append, lambda _session: runtime)
        for coroutine in scheduled:
            coroutine.close()
        return len(scheduled)

    def test_expiry_below_token_gate_does_not_compact(self) -> None:
        self.assertEqual(self.run_scan(69999), 0)

    def test_expiry_at_token_gate_forces_compaction(self) -> None:
        self.assertEqual(self.run_scan(70000), 1)


if __name__ == "__main__":
    unittest.main()
