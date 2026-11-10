# [[file:../../../../../agents-hermes-escalation.org::test-hermes-escalation-ledger][test-hermes-escalation-ledger]]
"""Escalation ledger regressions; generated from agents-hermes-escalation.org."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

PLUGIN = Path(os.environ["ESCALATION_LEDGER_UNDER_TEST"])
spec = importlib.util.spec_from_file_location("escalation_ledger_test_target", PLUGIN)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

NOW = 1_800_000_000.0


class Ledger(unittest.TestCase):
    AREA = "FORGE/centre-apps/crystal-merge"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "--quiet", str(self.repo)], check=True, capture_output=True)
        self.saved = (m.REPOS, m.STATE_DB, m.STATE_DIR, m.USAGE_CMD)
        m.REPOS = [self.repo]
        m.STATE_DB = base / "state.db"
        m.STATE_DIR = base / "state"
        m.STATE_DIR.mkdir()
        m.USAGE_CMD = None
        self.addCleanup(self.restore)
        self.n = 0
        self.called = 0

    def restore(self):
        m.REPOS, m.STATE_DB, m.STATE_DIR, m.USAGE_CMD = self.saved

    def commit(self, path, subject="work", author="Hermes", age_h=1.0):
        self.n += 1
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("v%d\n" % self.n)
        when = "%d +0000" % int(NOW - age_h * 3600)
        env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
        subprocess.run(["git", "-C", str(self.repo), "add", path], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "core.hooksPath=/dev/null", "-c", "user.name=" + author,
                        "-c", "user.email=a@example.invalid", "commit", "--quiet", "-m", subject],
                       check=True, capture_output=True, env=env)

    def sessions(self, rows):
        con = sqlite3.connect(str(m.STATE_DB))
        con.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT, started_at REAL, estimated_cost_usd REAL, "
                    "actual_cost_usd REAL, tool_call_count INTEGER)")
        con.executemany("INSERT INTO sessions VALUES (?,?,?,?,?)", rows)
        con.commit()
        con.close()

    def status(self):
        return m.status(NOW)

    def nxt(self, args):
        self.called += 1
        return {"ran": True}

    def test_revert_by_hermes_is_a_strike(self):
        self.commit(self.AREA + "/a.css", "revert(crystal-merge): back")
        self.assertEqual(1, self.status()["areas"][self.AREA]["strikes"])

    def test_revert_by_someone_else_is_not(self):
        self.commit(self.AREA + "/a.css", "Revert: x", author="Ecco")
        self.assertNotIn(self.AREA, self.status()["areas"])

    def test_old_revert_outside_window_is_ignored(self):
        self.commit(self.AREA + "/a.css", "revert: old", age_h=30)
        self.assertNotIn(self.AREA, self.status()["areas"])

    def test_churn_is_a_strike_beyond_the_threshold(self):
        for i in range(5):
            self.commit(self.AREA + "/f%d.css" % i, "fix: %d" % i)
        self.assertNotIn(self.AREA, self.status()["areas"])
        self.commit(self.AREA + "/f9.css", "fix: nine")
        self.assertEqual(1, self.status()["areas"][self.AREA]["strikes"])

    def test_churn_in_other_areas_is_counted_separately(self):
        for i in range(3):
            self.commit(self.AREA + "/f%d" % i, "fix")
            self.commit("FORGE/centre-apps/jewels/f%d" % i, "fix")
        self.assertEqual({}, self.status()["areas"])

    def test_recorded_rejections_are_strikes(self):
        m.record_rejection(self.AREA, "it looks wrong", now=NOW - 600)
        self.assertEqual(1, self.status()["areas"][self.AREA]["strikes"])

    def test_old_rejection_is_ignored(self):
        m.record_rejection(self.AREA, "old", now=NOW - 40 * 3600)
        self.assertEqual({}, self.status()["areas"])

    def test_levels_follow_the_thresholds(self):
        m.record_rejection(self.AREA, "one", now=NOW - 60)
        self.assertEqual("ok", self.status()["areas"][self.AREA]["level"])
        m.record_rejection(self.AREA, "two", now=NOW - 50)
        self.assertEqual("review", self.status()["areas"][self.AREA]["level"])
        m.record_rejection(self.AREA, "three", now=NOW - 40)
        self.assertEqual("stop", self.status()["areas"][self.AREA]["level"])

    def test_cost_over_cap_requires_review(self):
        self.sessions([("s", NOW - 3600, 3.5, None, 10)])
        result = self.status()
        self.assertEqual("review", result["level"])
        self.assertIn("cost", " ".join(result["reasons"]))

    def test_cost_under_cap_is_quiet(self):
        self.sessions([("s", NOW - 3600, 1.0, None, 10)])
        self.assertEqual("ok", self.status()["level"])

    def test_actual_cost_preferred_over_estimate(self):
        self.sessions([("s", NOW - 3600, 9.0, 0.5, 10)])
        self.assertEqual("ok", self.status()["level"])

    def test_tool_call_cap_requires_review(self):
        self.sessions([("a", NOW - 100, 0.1, None, 300), ("b", NOW - 200, 0.1, None, 150)])
        self.assertEqual("review", self.status()["level"])

    def test_old_sessions_do_not_count(self):
        self.sessions([("s", NOW - 40 * 3600, 99.0, None, 9999)])
        self.assertEqual("ok", self.status()["level"])

    def test_missing_session_store_is_reported_not_hidden(self):
        result = self.status()
        self.assertEqual("ok", result["level"])
        self.assertTrue(result["unavailable"])

    USAGE = [
        {"provider": "claude", "state": "ok", "raw": {"usage": {"primary": {"usedPercent": 40}, "secondary": {"usedPercent": 10}}}},
        {"provider": "codex", "state": "ok", "raw": {"usage": {"primary": {"usedPercent": 95}, "secondary": {"usedPercent": 20}}}},
        {"provider": "gemini", "state": "error", "raw": {}},
        {"provider": "openrouter", "state": "ok", "raw": {"usage": {}}},
    ]

    def test_headroom_uses_the_tighter_window(self):
        h = m.headroom(self.USAGE)
        self.assertEqual(60, h["claude"])
        self.assertEqual(5, h["codex"])

    def test_errored_or_empty_provider_has_no_headroom_evidence(self):
        h = m.headroom(self.USAGE)
        self.assertIsNone(h.get("gemini"))
        self.assertIsNone(h.get("openrouter"))

    def test_next_rung_prefers_flat_rate_with_headroom(self):
        rung, why = m.next_rung(-1, m.headroom(self.USAGE))
        self.assertEqual("claude-sonnet", rung["name"])

    def test_next_rung_never_guesses_missing_headroom(self):
        rung, why = m.next_rung(-1, {})
        self.assertIsNone(rung)
        self.assertTrue(any("no live headroom" in line for line in why))

    def test_next_rung_skips_exhausted_provider_with_a_reason(self):
        rung, why = m.next_rung(-1, {"codex": 5, "claude": 70, "gemini": 50})
        self.assertEqual("claude-sonnet", rung["name"])
        self.assertTrue(any("codex" in line and "5" in line for line in why))

    def test_next_rung_advances_past_the_current_rung(self):
        h = {"codex": 80, "claude": 80, "gemini": 80}
        first, _ = m.next_rung(-1, h)
        second, _ = m.next_rung(m.LADDER.index(first), h)
        self.assertGreater(m.LADDER.index(second), m.LADDER.index(first))

    def test_top_of_the_ladder_returns_nothing(self):
        rung, why = m.next_rung(len(m.LADDER) - 1, {"claude": 90})
        self.assertIsNone(rung)

    def test_metered_rung_used_when_no_flat_rate_has_room(self):
        rung, why = m.next_rung(-1, {"codex": 1, "claude": 2, "gemini": 90})
        self.assertEqual("gemini-flash", rung["name"])

    def publish(self):
        return m.gate("terminal", {"command": "python3 FORGE/centre-apps/publish.py stage_apps"},
                      self.nxt, session_id="s1")

    def receipt(self, **overrides):
        shot = Path(self.tmp.name) / "shot.png"
        shot.write_bytes(b"png")
        data = {"area": self.AREA, "reviewer": "auryn", "author": "hermes-agent", "screenshot": str(shot),
                "spec": "spec.md", "verdict": "pass", "ts": NOW}
        data.update(overrides)
        m.record_review(**data)

    def test_publish_refused_when_hermes_changed_an_area_unreviewed(self):
        self.commit(self.AREA + "/a.css", "fix: grass")
        self.assertIn("ESCALATION LEDGER REFUSED", self.publish())
        self.assertEqual(0, self.called)

    def test_publish_admitted_with_a_valid_independent_receipt(self):
        self.commit(self.AREA + "/a.css", "fix: grass")
        self.receipt()
        self.assertTrue(self.publish().get("ran"))

    def test_self_review_does_not_count(self):
        self.commit(self.AREA + "/a.css", "fix: grass")
        self.receipt(reviewer="hermes-agent")
        self.assertIn("ESCALATION LEDGER REFUSED", self.publish())

    def test_missing_screenshot_does_not_count(self):
        self.commit(self.AREA + "/a.css", "fix: grass")
        self.receipt(screenshot="/nonexistent/shot.png")
        self.assertIn("ESCALATION LEDGER REFUSED", self.publish())

    def test_failed_verdict_does_not_count(self):
        self.commit(self.AREA + "/a.css", "fix: grass")
        self.receipt(verdict="fail")
        self.assertIn("ESCALATION LEDGER REFUSED", self.publish())

    def test_receipt_older_than_the_change_does_not_count(self):
        self.receipt(ts=NOW - 7200)
        self.commit(self.AREA + "/a.css", "fix: grass", age_h=1)
        self.assertIn("ESCALATION LEDGER REFUSED", self.publish())

    def test_publish_allowed_when_hermes_changed_nothing(self):
        self.commit(self.AREA + "/a.css", "fix: grass", author="Ecco")
        self.assertTrue(self.publish().get("ran"))

    def test_other_terminal_commands_are_untouched(self):
        self.commit(self.AREA + "/a.css", "fix: grass")
        result = m.gate("terminal", {"command": "git status"}, self.nxt, session_id="s1")
        self.assertTrue(result.get("ran"))

    def test_publish_fails_closed_when_history_is_unreadable(self):
        m.REPOS = [Path(self.tmp.name) / "missing"]
        self.assertIn("ESCALATION LEDGER REFUSED", self.publish())

    def test_stopped_area_blocks_structured_writes_under_it(self):
        for text in ("a", "b", "c"):
            m.record_rejection(self.AREA, text, now=NOW - 60)
        target = str(self.repo / self.AREA / "x.css")
        refused = m.gate("write_file", {"path": target}, self.nxt, session_id="s1", now=NOW)
        self.assertIn("ESCALATION LEDGER REFUSED", refused)
        other = m.gate("write_file", {"path": str(self.repo / "docs/x.md")}, self.nxt, session_id="s1", now=NOW)
        self.assertTrue(other.get("ran"))

    def test_review_level_alone_does_not_block_writes(self):
        for text in ("a", "b"):
            m.record_rejection(self.AREA, text, now=NOW - 60)
        target = str(self.repo / self.AREA / "x.css")
        self.assertTrue(m.gate("write_file", {"path": target}, self.nxt, session_id="s1", now=NOW).get("ran"))

    def test_context_is_silent_when_everything_is_ok(self):
        self.sessions([("s", NOW - 60, 0.1, None, 1)])
        self.assertEqual("", m.inject_state(now=NOW)["context"])

    def test_context_names_the_area_strikes_and_next_rung(self):
        for text in ("a", "b"):
            m.record_rejection(self.AREA, text, now=NOW - 60)
        (m.STATE_DIR / "usage.json").write_text(json.dumps({"fetched": NOW, "items": self.USAGE}))
        text = m.inject_state(now=NOW)["context"]
        for word in (self.AREA, "2 strikes", "claude-sonnet", "verbatim"):
            self.assertIn(word, text)

    def test_context_admits_missing_usage_evidence(self):
        for text in ("a", "b"):
            m.record_rejection(self.AREA, text, now=NOW - 60)
        self.assertIn("no live headroom", m.inject_state(now=NOW)["context"])

    def test_policy_override_file_is_honoured(self):
        (m.STATE_DIR / "policy.json").write_text(json.dumps({"review_strikes": 1}))
        m.record_rejection(self.AREA, "one", now=NOW - 60)
        self.assertEqual("review", self.status()["areas"][self.AREA]["level"])

    def test_corrupt_policy_file_falls_back_to_defaults(self):
        (m.STATE_DIR / "policy.json").write_text("{")
        self.assertEqual("ok", self.status()["level"])

    def test_registers_hooks(self):
        seen = []

        class Ctx:
            def register_middleware(self, name, callback):
                seen.append(("middleware", name))

            def register_hook(self, name, callback):
                seen.append(("hook", name))

        m.register(Ctx())
        self.assertEqual([("middleware", "tool_execution"), ("hook", "pre_llm_call")], seen)


if __name__ == "__main__":
    unittest.main()
# test-hermes-escalation-ledger ends here
