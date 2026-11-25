#!/usr/bin/env python3
"""Tests for CLAUDE_IDLE_COMPACT_MODE=deterministic in claude-warm.

No real process is forked, no real ~/.claude session is read or written: pty.fork,
os.execvpe, the child stop and launch are all faked, and every path the pass
touches is under a temporary directory (CLAUDE_PROJECTS_DIR /
CLAUDE_IDLE_COMPACT_STATE_DIR are the production overrides the tests drive).

Run: python3 test-offline-compact-mode.py
"""
from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import sqlite3
import stat
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
WARM = ROOT / "all/.local/bin/claude-warm"
MODULE = ROOT / "all/.local/lib/dotcortex/offline_compact.py"
LANDED_TOOL = Path(
    os.environ.get(
        "COMPACT_OFFLINE_TOOL",
        "/home/metsatron/HelmCortex/FORGE/scripts/context_retention/compact_offline.py",
    )
)

SESSION = "123e4567-e89b-42d3-a456-426614174000"

# The compaction engine is imported once; the supervisor loads the same file in
# production through CLAUDE_WARM_OFFLINE_COMPACT_MODULE / the lib path.
os.environ.setdefault("CLAUDE_WARM_OFFLINE_COMPACT_MODULE", str(MODULE))


def load_module(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # dataclass() resolves annotations via sys.modules[cls.__module__].
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_written(fd: int) -> bytes:
    os.set_blocking(fd, False)
    try:
        return os.read(fd, 8192)
    except BlockingIOError:
        return b""


def build_transcript(
    path: Path,
    *,
    big: int = 10,
    tail: int = 60,
    tool_chars: int = 120_000,
    human_chars: int = 0,
    session_id: str = SESSION,
) -> list[dict]:
    """Write a synthetic transcript: big tool_result records, then a protected tail."""
    rows = []
    previous = None
    for index in range(big + tail):
        uid = str(uuid.uuid4())
        row = {
            "type": "user" if index % 2 == 0 else "assistant",
            "uuid": uid,
            "parentUuid": previous,
            "sessionId": session_id,
            "timestamp": "2026-11-18T09:%02d:%02dZ" % (index // 60, index % 60),
        }
        if index < big:
            blocks = [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_%d" % index,
                    "content": "first line of output %d\n" % index + "x" * tool_chars,
                }
            ]
            if human_chars:
                blocks.append({"type": "text", "text": "operator note %d: " % index + "y" * human_chars})
            row["message"] = {"role": "user", "content": blocks}
        else:
            row["message"] = {
                "role": "assistant",
                "content": [{"type": "text", "text": "closing note %d" % index}],
            }
        rows.append(row)
        previous = uid
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return rows


class Recorder:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def __call__(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))

    def names(self) -> list[str]:
        return [name for name, _fields in self.events]

    def find(self, name: str) -> list[dict]:
        return [fields for event, fields in self.events if event == name]


class Harness:
    """A Supervisor built without __init__, with every side effect faked."""

    def __init__(self, warm, tmp: Path, *, mode: str, usage_limit_until=None, tokens=300_000):
        self.tmp = tmp
        self.projects = tmp / "projects"
        self.project = self.projects / "-home-agent-work"
        self.project.mkdir(parents=True)
        self.state_dir = tmp / "state"
        self.transcript = self.project / ("%s.jsonl" % SESSION)
        self.rows = build_transcript(self.transcript)

        obj = warm.Supervisor.__new__(warm.Supervisor)
        obj.enabled = True
        obj.status = "idle"
        obj.compacting = False
        obj.session_id = SESSION
        obj.channel = "claude-" + "a" * 32
        obj.dirty = True
        obj.usage_limit_until = usage_limit_until
        obj.current_tokens = tokens
        obj.current_model = "claude-test"
        obj.post_compact_baseline_tokens = 0
        obj.post_compact_baseline_at = None
        obj.last_normal_stop = time.time() - 100
        obj.last_lifecycle_activity = None
        obj.last_local_input = None
        obj.transcript_activity_at = None
        obj.transcript_path = self.transcript
        obj.transcript_project_dir = self.project
        obj.transcript_gate_blocked = False
        obj.transcript_gate_blocked_at = None
        obj.transcript_quiescence_deadline = None
        obj.transcript_baseline = None
        obj.transcript_inode = None
        obj.transcript_offset = 0
        obj.transcript_partial = b""
        obj.recovery_pending = False
        obj.recovery_callable = None
        obj.recovery_command = None
        obj.preservation_state = None
        obj.preservation_request_id = None
        obj.cache_ttl_seconds = 3600
        # The idle window this fixture used to reach the pass by size alone is
        # now the cold-boundary trigger's input: 100s idle against a 60s
        # compact-before window is a COLD cache, so the mechanics tests keep
        # testing the pass rather than the trigger.  The trigger tests set their
        # own values.
        obj.cache_idle_seconds = 60
        # A precomputed harness keeps these tests independent of this host's
        # instruction files; the harness tests supply their own numbers.
        obj.harness_baseline_cache = {
            "harness_tokens": 0,
            "harness_source": "test-fixture",
            "harness_files": [],
        }
        obj.watched_servers = ()
        obj.development_channel_opt_ins = ()
        obj.timer_generation = 0
        obj.timer_deadline = None
        obj.timer_kind = None
        obj.last_gate_rejection_reason = None
        obj.last_cancellation_reason = None
        obj.last_state_transition = None
        obj.last_injection_result = None
        obj.compaction_requested_at = None
        obj.compaction_ignore_next_stop = False
        obj.compact_mode = mode
        obj.compact_projects_dir = self.projects
        obj.offline_compact_root = self.state_dir
        obj.offline_compact_ceiling = 70_000
        obj.offline_compact_chars_per_token = 4.0
        obj.offline_compact_stage = None
        obj.session_override = None
        obj.argv = ["claude", "--resume", SESSION]
        obj.decider_mod_path = tmp / "no-mod"
        obj.pid = os.getpid()  # a live pid, so child_alive() passes without forking
        obj.child_status = None
        obj.child_tty = None
        obj.child_tty_device = None
        obj.mailcortex_input_dirty = False
        obj._pty_still_owned = lambda: True
        obj._injection_idle_boundary = lambda purpose: 0
        obj._idle_window_open = lambda: False
        obj._read_snapshot = lambda: ({}, None)
        obj._refresh_cache_policy_for_action = lambda: True
        obj._gate_reason = lambda purpose: None
        obj._decider_summary_ready = lambda: False
        obj.rearm = lambda *args, **kwargs: None
        obj._debug = lambda *args, **kwargs: None
        obj.guard = Recorder()
        obj._guard_log = obj.guard
        obj._write_state = lambda: None
        obj.launches = []
        obj.stops = 0
        obj.launch = self.fake_launch
        obj._stop_child_for_relaunch = self.fake_stop
        read_fd, write_fd = os.pipe()
        self.read_fd = read_fd
        self.write_fd = write_fd
        obj.master_fd = write_fd
        self.obj = obj

    def fake_launch(self):
        self.obj.launches.append(self.obj._child_argv())
        self.obj.pid = 4242

    def fake_stop(self):
        self.obj.stops += 1
        self.obj.pid = None
        return True

    def installed_sessions(self) -> list[Path]:
        return sorted(
            path
            for path in self.project.glob("*.jsonl")
            if path.name != self.transcript.name
        )

    @property
    def stops(self) -> int:
        return self.obj.stops

    def close(self) -> None:
        os.close(self.read_fd)
        os.close(self.write_fd)


class OfflineCompactModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.warm = load_module(WARM, "claude_warm_offline_compact")
        # The SAME module object the supervisor loads: patching it in a test must
        # affect the code under test, not a second copy of the file.
        cls.module = cls.warm._offline_compact_module()
        assert cls.module is not None and cls.module.__file__ == str(MODULE)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.tmp = Path(self.directory.name)
        self.harnesses = []

    def tearDown(self):
        for harness in self.harnesses:
            harness.close()
        self.directory.cleanup()

    def harness(self, **kwargs) -> Harness:
        harness = Harness(self.warm, self.tmp, **kwargs)
        self.harnesses.append(harness)
        return harness

    # -- 1. the native default is untouched -------------------------------

    def test_native_mode_still_injects_compact(self):
        harness = self.harness(mode="native")
        obj = harness.obj
        self.assertTrue(obj.attempt(command="/compact", purpose="compact"))
        self.assertEqual(read_written(harness.read_fd), b"/compact\r")
        self.assertIn("injection-attempted", obj.guard.names())
        self.assertFalse(any(name.startswith("offline-compact:") for name in obj.guard.names()))
        self.assertEqual(harness.installed_sessions(), [])
        self.assertEqual(obj.session_id, SESSION)

    # -- 2. deterministic installs a compacted copy, never writes /compact -

    def test_deterministic_installs_compacted_session_and_never_writes_compact(self):
        harness = self.harness(mode="deterministic", usage_limit_until=time.time() + 600)
        obj = harness.obj
        source_digest = hashlib.sha256(harness.transcript.read_bytes()).hexdigest()

        self.assertTrue(obj.attempt(command="/compact", purpose="compact"))

        # nothing reached the PTY
        self.assertEqual(read_written(harness.read_fd), b"")
        self.assertNotIn("injection-attempted", obj.guard.names())

        installed = harness.installed_sessions()
        self.assertEqual(len(installed), 1, installed)
        new_session = installed[0].stem
        self.assertNotEqual(new_session, SESSION)
        self.assertEqual(str(uuid.UUID(new_session, version=4)), new_session)
        self.assertEqual(stat.S_IMODE(installed[0].stat().st_mode), 0o600)

        records = [json.loads(line) for line in installed[0].read_text().splitlines() if line.strip()]
        self.assertEqual(len(records), len(harness.rows))
        self.assertTrue(all(record["sessionId"] == new_session for record in records))

        # chain preserved, identity preserved, source untouched
        source_chain = self.module.parent_chain(harness.rows)
        installed_chain = self.module.parent_chain(records)
        self.assertEqual(len(installed_chain), len(source_chain))
        self.assertEqual(installed_chain, source_chain)
        self.assertEqual(
            [record["uuid"] for record in records], [row["uuid"] for row in harness.rows]
        )
        self.assertEqual(
            hashlib.sha256(harness.transcript.read_bytes()).hexdigest(), source_digest
        )

        # the oversized tool output was elided, the session is under the ceiling
        compacted = json.loads(
            next(
                iter(
                    Path(obj.offline_compact_root).glob("*/*/archive/compaction-report.json")
                )
            ).read_text()
        )
        self.assertGreater(compacted["est_tokens_before"], 70_000)
        self.assertLessEqual(compacted["est_tokens_after"], 70_000)
        self.assertTrue(compacted["ceiling_met"])
        self.assertEqual(compacted["index_entries"], compacted["elided_blocks"])
        self.assertGreater(compacted["index_entries"], 0)
        self.assertEqual(
            compacted["index_entries"], compacted["selected_for_elision"]
        )
        self.assertEqual(
            compacted["elided_blocks"] + compacted["kept_verbatim"],
            compacted["elidable_candidates"],
        )

        # the seat moved to the new session and relaunched on it
        self.assertEqual(obj.session_id, new_session)
        self.assertEqual(obj.session_override, new_session)
        self.assertEqual(harness.stops, 1)
        self.assertEqual(len(obj.launches), 1)
        self.assertIn("--resume", obj.launches[0])
        self.assertEqual(obj.launches[0][obj.launches[0].index("--resume") + 1], new_session)
        self.assertFalse(obj.dirty)
        self.assertIn("offline-compact:relaunched", obj.guard.names())
        self.assertTrue(
            any(fields.get("session") == new_session for fields in obj.guard.find("offline-compact:installed"))
        )

    # -- 3. a human-words change refuses and leaves the seat alone --------

    def test_deterministic_human_words_change_refuses_without_compact(self):
        harness = self.harness(mode="deterministic", usage_limit_until=time.time() + 600)
        obj = harness.obj
        real_compact = self.module.compact

        def dishonest(source, out, archive, **kwargs):
            result = real_compact(source, out, archive, **kwargs)
            result.report["human_words_changed"] = 1
            return result

        self.module.compact = dishonest
        try:
            self.assertFalse(obj.attempt(command="/compact", purpose="compact"))
        finally:
            self.module.compact = real_compact

        self.assertEqual(read_written(harness.read_fd), b"")
        self.assertEqual(harness.installed_sessions(), [])
        self.assertEqual(obj.session_id, SESSION)
        self.assertEqual(harness.stops, 0)
        self.assertEqual(obj.launches, [])
        failures = obj.guard.find("offline-compact:failed")
        self.assertTrue(failures)
        self.assertEqual(failures[-1]["reason"], "human-words-changed")

    # -- 4. a shorter post-compaction chain refuses the swap --------------

    def test_deterministic_shorter_chain_refuses(self):
        harness = self.harness(mode="deterministic", usage_limit_until=time.time() + 600)
        obj = harness.obj
        real_chain = self.module.parent_chain

        def truncated(records):
            chain = real_chain(records)
            # Only the INSTALLED copy (rewritten to the new session id) loses
            # records: the compactor's own checks stay honest.
            if records and records[0].get("sessionId") != SESSION:
                return chain[:-3]
            return chain

        self.module.parent_chain = truncated
        try:
            self.assertFalse(obj.attempt(command="/compact", purpose="compact"))
        finally:
            self.module.parent_chain = real_chain

        self.assertEqual(read_written(harness.read_fd), b"")
        self.assertEqual(harness.installed_sessions(), [], "the installed copy must be removed")
        self.assertEqual(obj.session_id, SESSION)
        self.assertEqual(harness.stops, 0)
        self.assertEqual(obj.launches, [])
        failures = obj.guard.find("offline-compact:failed")
        self.assertTrue(failures)
        self.assertEqual(failures[-1]["reason"], "chain-mismatch")

    # -- 5. usage-limited: no /compact is attempted at all ----------------

    def test_deterministic_usage_limited_never_attempts_compact(self):
        harness = self.harness(mode="deterministic", usage_limit_until=time.time() + 900)
        obj = harness.obj

        def boom(*args, **kwargs):
            raise RuntimeError("compactor exploded")

        real_compact = self.module.compact
        self.module.compact = boom
        try:
            self.assertFalse(obj.attempt(command="/compact", purpose="compact"))
        finally:
            self.module.compact = real_compact

        self.assertEqual(read_written(harness.read_fd), b"")
        self.assertEqual(harness.stops, 0)
        self.assertEqual(obj.launches, [])
        self.assertEqual(obj.session_id, SESSION)
        self.assertIn("offline-compact:failed", obj.guard.names())
        waiting = obj.guard.find("offline-compact:waiting")
        self.assertTrue(waiting)
        self.assertEqual(waiting[-1]["reason"], "compactor-error")
        self.assertNotIn("injection-attempted", obj.guard.names())
        self.assertNotIn("compaction-requested", obj.guard.names())

    # -- failure without a usage hold falls back to the native path -------

    def test_deterministic_session_under_ceiling_never_spends_paid_compact(self):
        harness = self.harness(mode="deterministic", usage_limit_until=None)
        obj = harness.obj
        # A small transcript: nothing needs eliding, so the pass must not hand
        # a paid /compact a turn just because the gate fired.
        self.assertTrue(obj.transcript_path.write_text(
            "\n".join(
                json.dumps(
                    {
                        "type": "user",
                        "uuid": "11111111-1111-4111-8111-111111111111",
                        "parentUuid": None,
                        "sessionId": SESSION,
                        "timestamp": "2026-11-18T09:00:00Z",
                        "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]},
                    }
                )
                for _ in range(3)
            )
            + "\n"
        ))
        self.assertFalse(obj.attempt(command="/compact", purpose="compact"))
        self.assertEqual(read_written(harness.read_fd), b"")
        refused = [
            fields
            for fields in obj.guard.find("offline-compact:refused")
            if fields.get("reason") == "no-elision-needed"
        ]
        self.assertTrue(refused, obj.guard.events)
        self.assertNotIn("offline-compact:native-fallback", obj.guard.names())
        self.assertEqual(harness.installed_sessions(), [])

    def test_deterministic_failure_without_usage_hold_falls_back_to_native(self):
        harness = self.harness(mode="deterministic", usage_limit_until=None)
        obj = harness.obj
        real_compact = self.module.compact
        self.module.compact = lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("compactor exploded")
        )
        try:
            self.assertTrue(obj.attempt(command="/compact", purpose="compact"))
        finally:
            self.module.compact = real_compact

        self.assertEqual(read_written(harness.read_fd), b"/compact\r")
        self.assertIn("offline-compact:native-fallback", obj.guard.names())
        self.assertEqual(harness.installed_sessions(), [])

    # -- 6. the ceiling trims the keep-set and the report shows both sizes -

    def test_ceiling_trims_keep_set_and_reports_both_sizes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            rows = build_transcript(source, big=9, tail=6, tool_chars=100_000)
            out = root / "out.jsonl"
            scores = {"r0-0": 0.99}
            for position in range(1, 9):
                scores["r%d-0" % position] = 0.01
            ranker = StubRanker(scores, self.module)

            result = self.module.compact(
                source,
                out,
                root / "archive",
                keep_recent_records=6,
                stub_over_chars=400,
                ceiling_tokens=70_000,
                chars_per_token=4.0,
                ranker=ranker,
            )

            self.assertTrue(result.ok, result.reason)
            report = result.report
            self.assertGreater(report["est_tokens_before"], 70_000)
            self.assertLessEqual(report["est_tokens_after"], 70_000)
            self.assertEqual(report["ceiling_tokens"], 70_000)
            self.assertTrue(report["ceiling_met"])
            self.assertEqual(report["tokenizer"], "chars/4")
            self.assertEqual(report["chars_per_token"], 4.0)
            self.assertIn("no provider tokenizer", report["token_estimate_basis"])
            self.assertEqual(report["selector"], "decider:stub")

            compacted = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
            kept = compacted[0]["message"]["content"][0]["content"]
            self.assertEqual(len(kept), len(rows[0]["message"]["content"][0]["content"]))
            elided = compacted[1]["message"]["content"][0]["content"]
            # R-0032 restated this pin: an elided block is a POINTER into the
            # retained transcript (path, line, char count), not a bare stub.
            self.assertIn("elided", elided)
            self.assertIn("line 2 of", elided)
            self.assertIn(str(source), elided)
            self.assertIn("{:,}".format(len(rows[1]["message"]["content"][0]["content"])), elided)
            self.assertLess(len(elided), 400)
            self.assertGreater(report["elided_blocks"], 1)
            self.assertGreaterEqual(report["kept_verbatim"], 1)
            self.assertEqual(report["pointer_stubs"], report["elided_blocks"])
            self.assertEqual(report["pointers_verified"], report["pointer_stubs"])
            self.assertEqual(report["pointer_mismatch_count"], 0)

    def test_ceiling_that_cannot_be_met_refuses_to_ship(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            # Human text is never elided: 12 x 40_000 chars is 120K tokens, so
            # no amount of tool-output elision can reach the 70K ceiling.
            build_transcript(source, big=12, tail=0, tool_chars=1_000, human_chars=40_000)
            result = self.module.compact(
                source, root / "out.jsonl", root / "archive", keep_recent_records=0
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.reason, "ceiling-not-met")
            self.assertGreater(result.report["est_tokens_after"], 70_000)
            self.assertFalse(result.report["ceiling_met"])
            self.assertIsNone(result.out_path)

    # -- 7. Decider unavailable -> deterministic fallback, labelled -------

    def test_decider_unavailable_runs_deterministic_fallback_labelled(self):
        # Port 9 on loopback refuses instantly: no network, no live endpoint.
        ranker = self.module.DeciderRanker(
            honey_url="http://127.0.0.1:9/decide", kikin_url=None, budget_ms=300
        )
        outcome = ranker.rank(
            [
                self.module.Candidate(
                    key="r0-0", position=0, block_index=0, chars=5000, uuid="u", excerpt="x"
                )
            ]
        )
        self.assertIn(outcome.selector, {"fallback:decider-unavailable", "fallback:decider-timeout"})
        self.assertFalse(outcome.usable)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            build_transcript(source, big=4, tail=2, tool_chars=90_000)
            result = self.module.compact(
                source, root / "out.jsonl", root / "archive", keep_recent_records=2, ranker=ranker
            )
            self.assertTrue(result.ok, result.reason)
            self.assertTrue(result.report["selector"].startswith("fallback:decider-"))
            self.assertNotEqual(result.report["decider_status"], "ok")

    def test_supervisor_logs_the_fallback_selector(self):
        harness = self.harness(mode="deterministic", usage_limit_until=time.time() + 600)
        obj = harness.obj
        previous = {key: os.environ.get(key) for key in (
            "CLAUDE_IDLE_COMPACT_DECIDER",
            "CLAUDE_IDLE_COMPACT_HONEY_DECIDER_URL",
            "CLAUDE_IDLE_COMPACT_KIKIN_DECIDER_URL",
            "SO_APPROVAL_HONEY_DECIDER_URL",
            "SO_APPROVAL_KIKIN_DECIDER_URL",
            "CLAUDE_IDLE_COMPACT_DECIDER_BUDGET_MS",
        )}
        os.environ["CLAUDE_IDLE_COMPACT_DECIDER"] = "auto"
        os.environ["CLAUDE_IDLE_COMPACT_HONEY_DECIDER_URL"] = "http://127.0.0.1:9/decide"
        os.environ["CLAUDE_IDLE_COMPACT_KIKIN_DECIDER_URL"] = ""
        os.environ.pop("SO_APPROVAL_HONEY_DECIDER_URL", None)
        os.environ.pop("SO_APPROVAL_KIKIN_DECIDER_URL", None)
        os.environ["CLAUDE_IDLE_COMPACT_DECIDER_BUDGET_MS"] = "300"
        try:
            self.assertTrue(obj.attempt(command="/compact", purpose="compact"))
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        compacted = obj.guard.find("offline-compact:compacted")
        self.assertTrue(compacted)
        self.assertTrue(str(compacted[-1]["selector"]).startswith("fallback:"), compacted[-1])
        self.assertIn("offline-compact:copy", obj.guard.names())

    # -- 8. nothing is dropped before its index entry exists --------------

    def test_nothing_is_dropped_before_its_index_entry_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            build_transcript(source, big=4, tail=2, tool_chars=90_000)
            out = root / "out.jsonl"
            index_db = root / "archive" / "index" / "elided.sqlite3"
            seen: list[str] = []

            def on_indexed(key: str, text: str) -> None:
                seen.append(key)
                connection = sqlite3.connect(str(index_db))
                try:
                    rows = connection.execute(
                        "SELECT chars FROM elided WHERE key = ?", (key,)
                    ).fetchall()
                    hits = [
                        row[0]
                        for row in connection.execute(
                            "SELECT key FROM elided WHERE elided MATCH ?", ("output",)
                        )
                    ]
                finally:
                    connection.close()
                self.assertTrue(rows, "the index row must be committed before the block is elided")
                self.assertEqual(rows[0][0], len(text))
                self.assertIn(key, hits, "the archived body must already be searchable")
                written = out.read_text() if out.exists() else ""
                # R-0032: the replacement is a pointer, so the absence to prove is
                # that no pointer for THIS record has been written yet.
                promised = "at line %d of" % (int(key[1:].split("-")[0]) + 1)
                self.assertNotIn(
                    promised, written, "no pointer may be written before its index row"
                )

            result = self.module.compact(
                source,
                out,
                root / "archive",
                keep_recent_records=2,
                stub_over_chars=400,
                ceiling_tokens=10_000,
                on_indexed=on_indexed,
            )
            self.assertTrue(result.ok, result.reason)
            self.assertEqual(len(seen), result.report["elided_blocks"])
            self.assertTrue(result.report["index_entries"] == len(seen))

    def test_index_failure_drops_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            build_transcript(source, big=4, tail=2, tool_chars=90_000)
            out = root / "out.jsonl"
            real_add = self.module.ElisionIndex.add
            calls = {"n": 0}

            def flaky(index, key, body, line=None):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise sqlite3.OperationalError("disk I/O error")
                return real_add(index, key, body, line)

            self.module.ElisionIndex.add = flaky
            try:
                result = self.module.compact(
                    source,
                    out,
                    root / "archive",
                    keep_recent_records=2,
                    stub_over_chars=400,
                    ceiling_tokens=10_000,
                )
            finally:
                self.module.ElisionIndex.add = real_add

            self.assertFalse(result.ok)
            self.assertEqual(result.reason, "index-or-write-failed")
            self.assertFalse(out.exists(), "a partial compacted copy must not survive")

    # -- the relaunch really goes through pty.fork + os.execvpe -----------

    def test_relaunch_execs_the_new_session_under_a_faked_pty(self):
        harness = self.harness(mode="deterministic")
        obj = harness.obj
        obj.session_override = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        obj.executable = "/usr/bin/claude"
        obj.session_dir = Path(obj.offline_compact_root)
        obj.socket_path = obj.session_dir / "control.sock"
        obj.watched_servers = ()
        obj.development_channel_opt_ins = ()
        obj.development_channel_accept_deadline = None
        obj.command_deadline = None
        obj._install_signals = lambda: None
        obj._install_terminal = lambda: None
        obj._register_herdr = lambda: None
        obj.herdr = type("Herdr", (), {"child_pid": None})()
        obj._write_state = lambda: None
        obj.selector = FakeSelector()
        obj.child_tty = None
        obj.child_tty_device = None

        recorded = {}

        def fake_fork():
            return 0, harness.write_fd

        def fake_exec(executable, argv, environment):
            recorded["argv"] = argv
            recorded["environment"] = dict(environment)
            raise SystemExit(0)

        real_fork, real_exec = self.warm.pty.fork, self.warm.os.execvpe
        real_exit, real_set_blocking = self.warm.os._exit, self.warm.os.set_blocking
        self.warm.pty.fork = fake_fork
        self.warm.os.execvpe = fake_exec
        self.warm.os._exit = lambda code: None
        self.warm.os.set_blocking = lambda fd, value: None
        try:
            self.warm.Supervisor.launch(obj)
        finally:
            self.warm.pty.fork = real_fork
            self.warm.os.execvpe = real_exec
            self.warm.os._exit = real_exit
            self.warm.os.set_blocking = real_set_blocking

        argv = recorded["argv"]
        self.assertEqual(argv[0], "/usr/bin/claude")
        self.assertIn("--resume", argv)
        self.assertEqual(argv[argv.index("--resume") + 1], obj.session_override)

    # -- argv rewriting ---------------------------------------------------

    def test_argv_with_session_rewrites_every_launcher_shape(self):
        new = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        self.assertEqual(
            self.warm.argv_with_session(["claude", "--resume", "old"], new),
            ["claude", "--resume", new],
        )
        self.assertEqual(
            self.warm.argv_with_session(["claude", "--resume=old"], new),
            ["claude", "--resume=" + new],
        )
        self.assertEqual(
            self.warm.argv_with_session(["claude", "--continue"], new),
            ["claude", "--resume", new],
        )
        self.assertEqual(
            self.warm.argv_with_session(["claude", "-c"], new),
            ["claude", "--resume", new],
        )
        self.assertEqual(
            self.warm.argv_with_session(["claude", "--model", "x"], new),
            ["--resume", new, "claude", "--model", "x"],
        )

    # -- policy parity with the landed standalone tool --------------------

    def test_stub_policy_matches_the_landed_compact_offline_tool(self):
        if not LANDED_TOOL.is_file():
            self.skipTest("compact_offline.py not present: %s" % LANDED_TOOL)
        landed = load_module(LANDED_TOOL, "landed_compact_offline")
        record = {
            "uuid": "u1",
            "parentUuid": None,
            "type": "user",
            "timestamp": "2026-11-18T09:00:00Z",
            "message": {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t", "content": "one\ntwo\n" + "z" * 900},
                    {"type": "text", "text": "human words"},
                ],
            },
        }
        self.assertEqual(self.module.STUB_TEMPLATE, landed.STUB_TEMPLATE)
        self.assertEqual(self.module.text_of_part(record["message"]["content"][0]),
                         landed.text_of_part(record["message"]["content"][0]))
        self.assertEqual(self.module.all_text(record), landed.all_text(record))
        self.assertEqual(self.module.human_text(record), landed.human_text(record))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            rows = build_transcript(source, big=3, tail=2, tool_chars=2_000)
            import contextlib
            import io

            with contextlib.redirect_stdout(io.StringIO()):
                code = landed.main(
                    [
                        "--source", str(source),
                        "--out", str(root / "landed.jsonl"),
                        "--archive", str(root / "landed-archive"),
                        "--keep-recent-records", "2",
                        "--stub-over-chars", "400",
                    ]
                )
            self.assertEqual(code, 0)
            ours = self.module.compact(
                source,
                root / "ours.jsonl",
                root / "our-archive",
                keep_recent_records=2,
                stub_over_chars=400,
                ceiling_tokens=1_000,
            )
            self.assertTrue(ours.ok, ours.reason)
            self.assertGreater(ours.report["elided_blocks"], 0)
            landed_rows = [
                json.loads(line)
                for line in (root / "landed.jsonl").read_text().splitlines()
                if line.strip()
            ]
            our_rows = [
                json.loads(line)
                for line in (root / "ours.jsonl").read_text().splitlines()
                if line.strip()
            ]
            self.assertEqual(len(landed_rows), len(our_rows))
            # Same stub policy, same key, same text: the landed tool stubs every
            # block over the limit, this engine stubs only as many as the ceiling
            # needs, so every block we elided must match the landed output byte
            # for byte and every block we kept must be one the tool would have cut.
            for position, (left, right) in enumerate(zip(landed_rows, our_rows)):
                landed_block = left["message"]["content"][0]
                our_block = right["message"]["content"][0]
                if not (isinstance(landed_block, dict) and "tool_use_id" in landed_block):
                    # a text record in the protected tail: identical, untouched
                    self.assertEqual(landed_block, our_block)
                    continue
                if "tool output elided" in our_block["content"]:
                    self.assertEqual(landed_block["content"], our_block["content"])
                else:
                    self.assertIn("tool output elided", landed_block["content"])
            self.assertEqual(
                [row["uuid"] for row in landed_rows], [row["uuid"] for row in rows]
            )


    # -- 9. R-0032: the COLD BOUNDARY is the trigger, not the token count -----

    def test_due_rule_reads_the_cache_not_the_transcript_size(self):
        due = self.warm.offline_compact_due
        self.assertEqual(
            due(status="idle", idle_age=10, cache_idle_seconds=3300, usage_limited=False),
            (False, "cache-warm"),
        )
        self.assertEqual(
            due(status="idle", idle_age=4000, cache_idle_seconds=3300, usage_limited=False),
            (True, "cache-cold"),
        )
        self.assertEqual(
            due(status="active", idle_age=4000, cache_idle_seconds=3300, usage_limited=False),
            (False, "seat-active"),
        )
        self.assertEqual(
            due(status="idle", idle_age=1, cache_idle_seconds=3300, usage_limited=True),
            (True, "usage-limited"),
        )
        self.assertEqual(
            due(status="active", idle_age=None, cache_idle_seconds=None, usage_limited=True),
            (False, "seat-active"),
        )
        self.assertEqual(
            due(status="idle", idle_age=None, cache_idle_seconds=None, usage_limited=False),
            (True, "cache-unmeasured"),
        )

    def test_warm_cache_and_idle_seat_do_not_run_the_pass(self):
        """A 900K-token session at a warm cache is the NORMAL state: do nothing."""
        harness = self.harness(mode="deterministic", tokens=900_000)
        obj = harness.obj
        obj.cache_idle_seconds = 3300  # 55 minutes of cache left
        obj.last_normal_stop = time.time() - 120  # two minutes idle: WARM

        self.assertFalse(obj.attempt(command="/compact", purpose="compact"))

        self.assertEqual(read_written(harness.read_fd), b"")
        self.assertEqual(harness.installed_sessions(), [])
        self.assertEqual(harness.stops, 0)
        self.assertEqual(obj.launches, [])
        trigger = obj.guard.find("offline-compact:trigger")[-1]
        self.assertFalse(trigger["due"])
        self.assertEqual(trigger["trigger"], "cache-warm")
        not_due = obj.guard.find("offline-compact:not-due")
        self.assertTrue(not_due, obj.guard.events)
        self.assertEqual(not_due[-1]["reason"], "cache-warm")
        # correct behaviour, never a failure and never a gate refusal
        self.assertNotIn("offline-compact:failed", obj.guard.names())
        self.assertNotIn("offline-compact:refused", obj.guard.names())
        self.assertNotIn("injection-attempted", obj.guard.names())

    def test_active_seat_never_compacts_however_cold_the_cache_is(self):
        harness = self.harness(mode="deterministic", tokens=900_000)
        obj = harness.obj
        obj.status = "active"
        obj.cache_idle_seconds = 1  # unequivocally cold
        obj.last_normal_stop = time.time() - 100_000

        self.assertFalse(obj.attempt(command="/compact", purpose="compact"))

        self.assertEqual(read_written(harness.read_fd), b"")
        self.assertEqual(harness.installed_sessions(), [])
        refused = obj.guard.find("offline-compact:refused")
        self.assertTrue(refused, obj.guard.events)
        self.assertEqual(refused[-1]["reason"], "session-active")

    def test_cold_cache_and_idle_seat_run_the_pass(self):
        harness = self.harness(mode="deterministic", tokens=300_000)
        obj = harness.obj
        obj.cache_idle_seconds = 60
        obj.last_normal_stop = time.time() - 300  # past the boundary

        self.assertTrue(obj.attempt(command="/compact", purpose="compact"))

        trigger = obj.guard.find("offline-compact:trigger")[-1]
        self.assertTrue(trigger["due"])
        self.assertEqual(trigger["trigger"], "cache-cold")
        self.assertEqual(len(harness.installed_sessions()), 1)

    def test_usage_limited_runs_the_pass_even_on_a_warm_cache(self):
        harness = self.harness(
            mode="deterministic", tokens=300_000, usage_limit_until=time.time() + 600
        )
        obj = harness.obj
        obj.cache_idle_seconds = 3300
        obj.last_normal_stop = time.time() - 30  # WARM: the paid path is blocked

        self.assertTrue(obj.attempt(command="/compact", purpose="compact"))

        trigger = obj.guard.find("offline-compact:trigger")[-1]
        self.assertEqual(trigger["trigger"], "usage-limited")
        self.assertTrue(trigger["due"])
        self.assertEqual(len(harness.installed_sessions()), 1)

    def test_tiny_session_under_the_floor_never_runs_the_pass(self):
        harness = self.harness(
            mode="deterministic", tokens=1_000, usage_limit_until=time.time() + 600
        )
        obj = harness.obj
        obj.cache_idle_seconds = 1
        obj.last_normal_stop = time.time() - 3_600

        self.assertFalse(obj.attempt(command="/compact", purpose="compact"))

        self.assertEqual(harness.installed_sessions(), [])
        self.assertEqual(read_written(harness.read_fd), b"")
        refused = obj.guard.find("offline-compact:refused")
        self.assertTrue(refused, obj.guard.events)
        self.assertEqual(refused[-1]["reason"], "below-token-threshold")
        # the floor is a floor: the trigger was never consulted
        self.assertEqual(obj.guard.find("offline-compact:trigger"), [])

    # -- 10. R-0032: an elided block becomes a LINE-NUMBER POINTER ------------

    def test_pointer_stub_names_the_source_line_and_char_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "90035468-c967-4a1b-8a2e-0123456789ab.jsonl"
            rows = build_transcript(source, big=4, tail=1, tool_chars=90_000)
            out = root / "out.jsonl"
            result = self.module.compact(
                source, out, root / "archive", keep_recent_records=1, ceiling_tokens=10_000
            )
            self.assertTrue(result.ok, result.reason)
            compacted = [
                json.loads(line) for line in out.read_text().splitlines() if line.strip()
            ]
            pointers = 0
            for index, record in enumerate(compacted):
                part = record["message"]["content"][0]
                if "elided" not in str(part.get("content")):
                    continue
                pointers += 1
                original = rows[index]["message"]["content"][0]["content"]
                self.assertEqual(
                    part["content"],
                    self.module.pointer_text(len(original), index + 1, str(source)),
                )
                self.assertIn(str(source), part["content"])
                self.assertIn("line %d of" % (index + 1), part["content"])
                self.assertIn("{:,} chars".format(len(original)), part["content"])
                self.assertLess(len(part["content"]), 400)
            self.assertGreater(pointers, 0)
            self.assertEqual(pointers, result.report["pointer_stubs"])

    def test_every_pointer_resolves_to_the_record_it_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            build_transcript(source, big=5, tail=1, tool_chars=90_000)
            result = self.module.compact(
                source,
                root / "out.jsonl",
                root / "archive",
                keep_recent_records=1,
                ceiling_tokens=10_000,
            )
            self.assertTrue(result.ok, result.reason)
            self.assertEqual(result.report["pointer_stubs"], result.report["elided_blocks"])
            self.assertEqual(
                result.report["pointers_verified"], result.report["pointer_stubs"]
            )
            self.assertEqual(result.report["pointer_mismatch_count"], 0)
            self.assertEqual(result.report["pointer_verification_basis"], "copy")

            # Independent re-check against the source file itself.
            lines = source.read_text().splitlines()
            compacted = [
                json.loads(line)
                for line in Path(result.report["out"]).read_text().splitlines()
                if line.strip()
            ]
            checked = 0
            for index, record in enumerate(compacted):
                part = record["message"]["content"][0]
                if "elided" not in str(part.get("content")):
                    continue
                match = re.search(r"at line (\d+) of", part["content"])
                self.assertIsNotNone(match)
                line_number = int(match.group(1))
                self.assertEqual(line_number, index + 1)
                named = json.loads(lines[line_number - 1])
                self.assertEqual(named["uuid"], record["uuid"])
                checked += 1
            self.assertGreater(checked, 0)
            self.assertEqual(checked, result.report["pointer_stubs"])

    def test_a_pointer_that_names_the_wrong_line_refuses_and_installs_nothing(self):
        harness = self.harness(mode="deterministic", usage_limit_until=time.time() + 600)
        obj = harness.obj
        real = self.module.pointer_text
        self.module.pointer_text = lambda chars, line, name: real(chars, line + 1, name)
        try:
            self.assertFalse(obj.attempt(command="/compact", purpose="compact"))
        finally:
            self.module.pointer_text = real

        self.assertEqual(read_written(harness.read_fd), b"")
        self.assertEqual(harness.installed_sessions(), [])
        self.assertEqual(obj.session_id, SESSION)
        self.assertEqual(harness.stops, 0)
        self.assertEqual(obj.launches, [])
        self.assertEqual(
            list(Path(obj.offline_compact_root).glob("*/*/compacted.jsonl")), [],
            "a refused output must not be left behind",
        )
        failures = obj.guard.find("offline-compact:failed")
        self.assertTrue(failures, obj.guard.events)
        self.assertEqual(failures[-1]["reason"], "pointer-mismatch")
        compacted = obj.guard.find("offline-compact:compacted")[-1]
        self.assertGreater(compacted["pointer_mismatch_count"], 0)
        self.assertEqual(compacted["pointers_verified"], 0)

    # -- 11. the ceiling is a cold RELOAD total: harness + conversation --------

    def test_harness_resolver_counts_one_global_and_exactly_one_scope_file(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".claude").mkdir()
            (home / ".claude" / "CLAUDE.md").write_text("g" * 4_000)
            (home / "HelmCortex").mkdir()
            (home / "HelmCortex" / "CLAUDE.md").write_text("s" * 40_000)
            # Present on disk, and must NOT be summed in for the Claude family.
            (home / "HelmCortex" / "AGENTS.md").write_text("a" * 60_000)

            baseline = self.module.resolve_harness("claude", "helmcortex", home=home)
            self.assertEqual(baseline.source, "measured")
            self.assertEqual([item["role"] for item in baseline.files], ["global", "scope"])
            self.assertTrue(baseline.files[0]["path"].endswith(".claude/CLAUDE.md"))
            self.assertTrue(baseline.files[1]["path"].endswith("HelmCortex/CLAUDE.md"))
            self.assertEqual(baseline.chars, 44_000)
            self.assertEqual(baseline.tokens, 11_000)

            codex = self.module.resolve_harness("codex", "helmcortex", home=home)
            self.assertEqual([item["role"] for item in codex.files], ["global", "scope"])
            self.assertTrue(codex.files[1]["path"].endswith("HelmCortex/AGENTS.md"))
            self.assertEqual(codex.chars, 64_000)
            self.assertEqual(codex.tokens, 16_000)

    def test_harness_resolver_refuses_two_scope_files(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".claude").mkdir()
            (home / ".claude" / "CLAUDE.md").write_text("g" * 400)
            helm = home / "HelmCortex"
            dot = home / "DotCortex"
            helm.mkdir()
            dot.mkdir()
            (helm / "CLAUDE.md").write_text("h" * 400)
            (dot / "CLAUDE.md").write_text("d" * 400)

            with self.assertRaises(self.module.HarnessScopeError):
                self.module.resolve_harness(
                    "claude",
                    "helmcortex",
                    home=home,
                    scope_files=[helm / "CLAUDE.md", dot / "CLAUDE.md"],
                )
            with self.assertRaises(self.module.HarnessScopeError):
                self.module.resolve_harness("claude", "helmcortex", home=home, scope_files=[])
            # HelmCortex and DotCortex are never summed for one seat either.
            single = self.module.resolve_harness(
                "claude", "dotcortex", home=home, scope_files=[dot / "CLAUDE.md"]
            )
            self.assertEqual(single.chars, 800)
            self.assertEqual(len(single.files), 2)

    def test_hermes_harness_is_excluded_not_modelled(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "HelmCortex").mkdir()
            (home / "HelmCortex" / "CLAUDE.md").write_text("x" * 400_000)
            baseline = self.module.resolve_harness("hermes", "helmcortex", home=home)
            self.assertEqual(baseline.tokens, 0)
            self.assertEqual(baseline.source, "excluded:hermes")
            self.assertEqual(baseline.files, [])

    def test_harness_falls_back_to_a_documented_estimate_and_says_so(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)  # no instruction files at all
            baseline = self.module.resolve_harness("claude", "helmcortex", home=home)
            self.assertEqual(baseline.source, "estimate:measurement-failed")
            self.assertEqual(baseline.tokens, self.module.DEFAULT_HARNESS_ESTIMATE_TOKENS)
            self.assertEqual(baseline.files, [])

    def test_harness_measurement_is_cached_per_seat_and_re_measured_on_change(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".claude").mkdir()
            (home / ".claude" / "CLAUDE.md").write_text("g" * 4_000)
            (home / "DotCortex").mkdir()
            scope = home / "DotCortex" / "CLAUDE.md"
            scope.write_text("s" * 8_000)
            cache = home / "state" / "harness-baseline.json"

            first = self.module.measure_harness(
                "claude", "dotcortex", home=home, cache_path=cache, seat="seat-a"
            )
            self.assertEqual((first.source, first.tokens), ("measured", 3_000))
            self.assertTrue(cache.is_file())

            cached = self.module.measure_harness(
                "claude", "dotcortex", home=home, cache_path=cache, seat="seat-a"
            )
            self.assertEqual((cached.source, cached.tokens), ("cache", 3_000))

            other_seat = self.module.measure_harness(
                "claude", "dotcortex", home=home, cache_path=cache, seat="seat-b"
            )
            self.assertEqual(other_seat.source, "measured")

            scope.write_text("s" * 12_000)  # the instruction file changed
            revised = self.module.measure_harness(
                "claude", "dotcortex", home=home, cache_path=cache, seat="seat-a"
            )
            self.assertEqual((revised.source, revised.tokens), ("measured", 4_000))

            override = self.module.measure_harness(
                "claude",
                "dotcortex",
                home=home,
                cache_path=cache,
                seat="seat-a",
                override_tokens=12_345,
            )
            self.assertEqual((override.source, override.tokens), ("override", 12_345))

    def test_harness_that_pushes_the_total_over_the_ceiling_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            # 10 text records x 22_000 chars = 55K conversation tokens: inside the
            # 70K ceiling on its own, outside a 50K conversation budget.
            rows = []
            previous = None
            for index in range(10):
                uid = str(uuid.uuid4())
                rows.append(
                    {
                        "type": "user",
                        "uuid": uid,
                        "parentUuid": previous,
                        "sessionId": SESSION,
                        "timestamp": "2026-11-18T09:%02d:00Z" % index,
                        "message": {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "note %d " % index + "y" * 22_000}
                            ],
                        },
                    }
                )
                previous = uid
            source.write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
            )

            alone = self.module.compact(
                source, root / "alone.jsonl", root / "archive-alone", keep_recent_records=0
            )
            self.assertEqual(alone.reason, "no-elision-needed")
            self.assertTrue(alone.report["ceiling_met"])
            self.assertEqual(alone.report["harness_tokens"], 0)
            self.assertEqual(alone.report["conversation_budget_tokens"], 70_000)
            self.assertEqual(
                alone.report["total_reload_tokens"], alone.report["est_tokens_after"]
            )

            harness = {
                "harness_family": "claude",
                "harness_scope": "helmcortex",
                "harness_tokens": 20_000,
                "harness_source": "test",
                "harness_files": [],
            }
            pushed = self.module.compact(
                source,
                root / "pushed.jsonl",
                root / "archive-pushed",
                keep_recent_records=0,
                harness=harness,
            )
            self.assertFalse(pushed.ok)
            self.assertEqual(pushed.reason, "ceiling-not-met")
            self.assertIsNone(pushed.out_path)
            self.assertEqual(pushed.report["harness_tokens"], 20_000)
            self.assertEqual(pushed.report["conversation_budget_tokens"], 50_000)
            self.assertGreater(pushed.report["total_reload_tokens"], 70_000)
            self.assertFalse(pushed.report["ceiling_met"])

            printed = json.loads(
                (root / "archive-pushed" / "compaction-report.json").read_text()
            )
            for key in ("harness_tokens", "conversation_budget_tokens", "total_reload_tokens"):
                self.assertIn(key, printed)
            self.assertEqual(
                printed["total_reload_tokens"],
                printed["harness_tokens"] + printed["est_tokens_after"],
            )

    def test_supervisor_reports_harness_budget_and_pointer_basis(self):
        harness = self.harness(mode="deterministic", usage_limit_until=time.time() + 600)
        obj = harness.obj
        obj.harness_baseline_cache = {
            "harness_family": "claude",
            "harness_scope": "helmcortex",
            "harness_tokens": 16_000,
            "harness_source": "measured",
            "harness_files": [
                {"role": "global", "path": "/home/x/.claude/CLAUDE.md", "chars": 15_555},
                {"role": "scope", "path": "/home/x/HelmCortex/CLAUDE.md", "chars": 48_930},
            ],
        }

        self.assertTrue(obj.attempt(command="/compact", purpose="compact"))

        compacted = obj.guard.find("offline-compact:compacted")[-1]
        self.assertEqual(compacted["harness_tokens"], 16_000)
        self.assertEqual(compacted["harness_source"], "measured")
        self.assertEqual(compacted["conversation_budget_tokens"], 54_000)
        self.assertLessEqual(compacted["total_reload_tokens"], 70_000)
        self.assertGreaterEqual(compacted["pointer_stubs"], 1)
        self.assertEqual(compacted["pointers_verified"], compacted["pointer_stubs"])
        self.assertEqual(compacted["pointer_mismatch_count"], 0)

        report = json.loads(
            next(
                iter(Path(obj.offline_compact_root).glob("*/*/archive/compaction-report.json"))
            ).read_text()
        )
        self.assertEqual(report["harness_tokens"], 16_000)
        self.assertEqual(report["conversation_budget_tokens"], 54_000)
        self.assertEqual(
            report["total_reload_tokens"], 16_000 + report["est_tokens_after"]
        )
        self.assertLessEqual(report["total_reload_tokens"], 70_000)
        self.assertEqual(report["pointer_verification_basis"], "pointer-source")
        self.assertEqual(
            [item["role"] for item in report["harness_files"]], ["global", "scope"]
        )
        self.assertEqual(obj.current_tokens, report["total_reload_tokens"])


class StubRanker:
    """A deterministic relevance selector for tests (no endpoint, no guessing)."""

    def __init__(self, scores: dict[str, float], module):
        self.scores = scores
        self.module = module

    def rank(self, candidates):
        keys = [candidate.key for candidate in candidates]
        return self.module.RankOutcome(
            scores={key: self.scores.get(key, 0.5) for key in keys},
            selector="decider:stub",
            status="ok",
            endpoint="stub",
            latency_ms=0,
            answered=len(keys),
        )


class FakeSelector:
    def __init__(self):
        self.registered = []
        self.unregistered = []

    def register(self, fileobj, events, data=None):
        self.registered.append((fileobj, data))
        return type("Key", (), {"data": data})()

    def unregister(self, fileobj):
        self.unregistered.append(fileobj)

    def select(self, timeout=None):
        return []


if __name__ == "__main__":
    unittest.main(verbosity=2)
