"""Unit tests for the Ductor idle-compaction seam (no network, no real CLI).

Loads idle_compact.py from the DotCortex seam directory (next to this tests
directory, or DOTCORTEX_DUCTOR_SEAMS) against the installed ductor_bot.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import importlib.util
import os
import sys

try:
    import ductor_bot  # noqa: F401  (the seam imports ductor_bot.cli.types)
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("ductor_bot is not installed")

_SEAMS = Path(os.environ.get("DOTCORTEX_DUCTOR_SEAMS", Path(__file__).resolve().parents[1] / "ductor-seams"))
_spec = importlib.util.spec_from_file_location("ductor_idle_compact_seam", _SEAMS / "idle_compact.py")
ic = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ic
_spec.loader.exec_module(ic)


@dataclass
class FakeSession:
    session_id: str
    provider: str
    last_active: str
    model: str = "m"
    reasoning_effort: str = ""
    chat_id: int = 1

    @property
    def session_key(self):
        return SimpleNamespace(chat_id=self.chat_id, topic_id=None, transport="tg", lock_key=(self.chat_id, None))


class FakeSessions:
    def __init__(self, sessions):
        self.sessions = sessions

    async def list_all(self):
        return list(self.sessions)

    async def get_active(self, key):
        for s in self.sessions:
            if s.chat_id == key.chat_id:
                return s
        return None


class FakeLockPool:
    def __init__(self):
        self.locks = {}

    def get(self, key):
        return self.locks.setdefault(key, asyncio.Lock())


@dataclass
class FakeCLI:
    calls: list = field(default_factory=list)

    async def execute(self, request):
        self.calls.append(request)
        return SimpleNamespace(is_error=False, result="", session_id=request.resume_session)


def ago(minutes: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()


class IdleCompactTests(unittest.IsolatedAsyncioTestCase):
    def make(self, sessions, config=None, busy=False):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "config").mkdir()
        (tmp / "config" / "config.json").write_text(json.dumps(config or {}))
        cli = FakeCLI()
        orch = SimpleNamespace(
            _paths=SimpleNamespace(
                sessions_path=tmp / "sessions.json",
                config_path=tmp / "config" / "config.json",
                workspace=tmp,
            ),
            _sessions=FakeSessions(sessions),
            _lock_pool=FakeLockPool(),
            _cli_service=cli,
            is_chat_busy=lambda chat_id, topic_id=None: busy,
        )
        comp = ic.IdleCompactor(orch)
        codex_calls = []

        async def fake_codex(session, settings):
            codex_calls.append(session.session_id)
            return True

        comp._compact_codex = fake_codex
        return comp, cli, codex_calls, tmp

    async def tick(self, comp):
        await comp._tick(comp._settings())

    async def test_claude_compacts_after_55_minutes_once(self):
        s = FakeSession("c1", "claude", ago(56))
        comp, cli, _, _ = self.make([s])
        await self.tick(comp)
        await self.tick(comp)
        self.assertEqual([r.prompt for r in cli.calls], ["/compact"])
        self.assertEqual(cli.calls[0].resume_session, "c1")

    async def test_claude_not_before_threshold(self):
        comp, cli, _, _ = self.make([FakeSession("c1", "claude", ago(40))])
        await self.tick(comp)
        self.assertEqual(cli.calls, [])

    async def test_codex_compacts_after_25_not_claude_window(self):
        comp, cli, codex, _ = self.make([FakeSession("x1", "codex", ago(26))])
        await self.tick(comp)
        self.assertEqual(codex, ["x1"])
        self.assertEqual(cli.calls, [])

    async def test_expired_cache_is_skipped_and_marked(self):
        comp, cli, codex, tmp = self.make(
            [FakeSession("x1", "codex", ago(31)), FakeSession("c1", "claude", ago(61), chat_id=2)]
        )
        await self.tick(comp)
        self.assertEqual((codex, cli.calls), ([], []))
        self.assertEqual(set(json.loads((tmp / "idle_compaction.json").read_text())), {"x1", "c1"})

    async def test_new_activity_rearms(self):
        s = FakeSession("c1", "claude", ago(56))
        comp, cli, _, _ = self.make([s])
        await self.tick(comp)
        s.last_active = ago(57)  # a later turn, idle again
        await self.tick(comp)
        self.assertEqual(len(cli.calls), 2)

    async def test_busy_chat_defers(self):
        comp, cli, _, _ = self.make([FakeSession("c1", "claude", ago(56))], busy=True)
        await self.tick(comp)
        self.assertEqual(cli.calls, [])

    async def test_config_overrides_and_disable(self):
        comp, cli, codex, _ = self.make(
            [FakeSession("x1", "codex", ago(21))], config={"idle_compaction": {"codex_idle_minutes": 20}}
        )
        await self.tick(comp)
        self.assertEqual(codex, ["x1"])
        comp2, cli2, _, _ = self.make([FakeSession("c1", "claude", ago(56))], config={"idle_compaction": {"enabled": False}})
        comp2.start()
        self.assertIsNone(comp2._task)

    async def test_state_survives_restart(self):
        s = FakeSession("c1", "claude", ago(56))
        comp, cli, _, tmp = self.make([s])
        await self.tick(comp)
        comp_b = ic.IdleCompactor(comp._orch)
        await self.tick(comp_b)
        self.assertEqual(len(cli.calls), 1)

    async def test_other_providers_ignored(self):
        comp, cli, codex, _ = self.make([FakeSession("g1", "gemini", ago(500))])
        await self.tick(comp)
        self.assertEqual((codex, cli.calls), ([], []))


if __name__ == "__main__":
    unittest.main()
