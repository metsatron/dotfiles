# [[file:../../../../../agents-hermes-protocol.org::test-hermes-protocol-gate][test-hermes-protocol-gate]]
"""Protocol admission regressions; generated from agents-hermes-protocol.org."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PLUGIN = Path(os.environ["PROTOCOL_GATE_UNDER_TEST"])
spec = importlib.util.spec_from_file_location("protocol_gate_test_target", PLUGIN)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Admission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.wt = Path(self.tmp.name) / "wt"
        self.wt.mkdir()
        self.courses = self.root / "ROOTS/PromptGolf/courses"
        self.holepath = self.courses / "HelmCortex/holes/active/test-hole.json"
        self.holepath.parent.mkdir(parents=True)
        self.hole = {"id": "test-hole", "course": "HelmCortex", "status": "in-progress",
                     "assigned_speaker": "hermes-agent", "planning_refs": ["project.md"],
                     "swings": [{"speaker": "hermes-agent", "session_id": "s1", "lie": None,
                                  "landed": None}]}
        self.save()
        self.registry = self.root / "ROOTS/PromptGolf/registry/worktree-map.json"
        self.registry.parent.mkdir(parents=True)
        self.registry.write_text(json.dumps({"worktrees": [{"course": "HelmCortex",
            "hole": "test-hole", "worktree": str(self.wt), "branch": "wt/test",
            "state": "commissioned"}]}))
        for rel in ("LOGS/TODO/HelmCortex.md", "ROOTS/Athanor/models.json", "project.md",
                    "FORGE/harness/userspace/PEER-AGENTS.md"):
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('{"models": []}' if p.suffix == '.json' else "# evidence\n- [ ] Operator priority unresolved\n")
        self.oldrepo, self.oldcourses = m.REPO, m.COURSES
        m.REPO, m.COURSES = self.root, self.courses
        self.addCleanup(self.restore)
        self.called = 0

    def restore(self):
        m.REPO, m.COURSES = self.oldrepo, self.oldcourses

    def save(self):
        self.holepath.write_text(json.dumps(self.hole))

    def next(self, args):
        self.called += 1
        return {"ran": True}

    def invoke(self, tool="write_file", args=None, session="s1"):
        return m.gate(tool, args or {"path": str(self.wt / "new.txt")}, self.next,
                      session_id=session, turn_id="t1")

    def refused(self, **kwargs):
        result = self.invoke(**kwargs)
        self.assertEqual(0, self.called, result)
        self.assertIn("error", result)
        return result

    def test_claimed_structured_write(self):
        self.assertTrue(self.invoke().get("ran"))

    def test_foreign_session_cannot_unlock(self):
        self.refused(session="someone-else")

    def test_missing_session_cannot_unlock(self):
        self.refused(session="")

    def test_foreign_swing_speaker_cannot_unlock(self):
        self.hole["swings"][0]["speaker"] = "orca"
        self.save()
        self.refused()

    def test_foreign_assignment_cannot_unlock(self):
        self.hole["assigned_speaker"] = "orca"
        self.save()
        self.refused()

    def test_closed_swing_cannot_unlock(self):
        self.hole["swings"][0]["lie"] = "fairway"
        self.save()
        self.refused()

    def test_landed_swing_cannot_unlock(self):
        self.hole["swings"][0]["landed"] = "receipt"
        self.save()
        self.refused()

    def test_queued_hole_cannot_unlock(self):
        self.hole["status"] = "queued"
        self.save()
        self.refused()

    def test_main_tree_write_refused(self):
        self.refused(args={"path": str(self.root / "project.md")})

    def test_unregistered_worktree_refused(self):
        other = Path(self.tmp.name) / "other-wt"
        other.mkdir()
        self.refused(args={"path": str(other / "file")})

    def test_symlink_escape_refused(self):
        (self.wt / "escape").symlink_to(self.root, target_is_directory=True)
        self.refused(args={"path": str(self.wt / "escape/project.md")})

    def test_worktree_alias_resolves(self):
        alias = Path(self.tmp.name) / "alias"
        alias.symlink_to(self.wt, target_is_directory=True)
        self.assertTrue(self.invoke(args={"path": str(alias / "new")}).get("ran"))

    def test_corrupt_ledger_fails_closed(self):
        self.holepath.write_text("{")
        self.refused()

    def test_corrupt_registry_fails_closed(self):
        self.registry.write_text("{")
        self.refused()

    def test_missing_sources_fails_closed(self):
        (self.root / "ROOTS/Athanor/models.json").unlink()
        self.refused()

    def test_missing_planning_ref_fails_closed(self):
        (self.root / "project.md").unlink()
        self.refused()

    def test_pre_llm_contains_canonical_evidence(self):
        text = m.inject_state(session_id="s1")["context"]
        for word in ("test-hole", "TODO", "Athanor", "PEER-AGENTS", "sha256", "Operator priority unresolved"):
            self.assertIn(word, text)
        self.assertNotIn("commit automatically closes", text)

    def test_pre_llm_reports_unclaimed(self):
        self.assertIn("UNCLAIMED", m.inject_state(session_id="wrong")["context"])

    def test_generic_python_requires_claim(self):
        self.refused(tool="execute_code", args={"code": "print('anything')"}, session="wrong")

    def test_unknown_tool_requires_claim(self):
        self.refused(tool="opaque_mutator", args={"id": 123}, session="wrong")

    def test_arbitrary_terminal_requires_claim(self):
        self.refused(tool="terminal", args={"command": "python3 -c 'print(1)'"}, session="wrong")

    def test_mail_read_recovery_without_claim(self):
        result = self.invoke(tool="terminal", args={"command": "mailcortex inbox hermes@kikin.helm"}, session="wrong")
        self.assertTrue(result.get("ran"))

    def test_read_chained_write_not_discovery(self):
        self.refused(tool="terminal", args={"command": "mailcortex inbox hermes@kikin.helm; touch stolen"}, session="wrong")

    def test_mail_send_requires_claim(self):
        self.refused(tool="terminal", args={"command": "mailcortex send --to orca --body x"}, session="wrong")

    def test_read_tools_available_for_recovery(self):
        self.assertTrue(self.invoke(tool="read_file", args={"path": str(self.holepath)}, session="wrong").get("ran"))

    def test_no_state_rewrite(self):
        before = self.holepath.read_bytes()
        self.invoke()
        self.assertEqual(before, self.holepath.read_bytes())

    def test_claim_errors_do_not_escape_middleware(self):
        with patch.object(m, "_claim", side_effect=OSError("fixture failure")):
            self.refused()

    def test_occupied_dispatch_refused_even_with_magic_words(self):
        foreign = dict(self.hole, id="occupied-lane", assigned_speaker="orca")
        self.holepath.with_name("occupied-lane.json").write_text(json.dumps(foreign))
        self.refused(tool="terminal", args={"command": "mailcortex send --from hermes@kikin.helm --to orca@kikin.helm --subject unit --body 'STAND DOWN occupied-lane; also do new work'"})

    def test_unreadable_dispatch_body_refused(self):
        self.refused(tool="terminal", args={"command": "mailcortex send --from hermes@kikin.helm --to orca@kikin.helm --subject unit --body-file /nonexistent/protocol-fixture"})

    def test_claimed_mail_not_sent_by_test(self):
        self.assertTrue(self.invoke(tool="terminal", args={"command": "mailcortex send --from hermes@kikin.helm --to orca@kikin.helm --subject receipt --body 'bounded acknowledgement'"}).get("ran"))
        self.assertEqual(1, self.called)

    def test_recovery_shell_expansion_refused(self):
        self.refused(tool="terminal", args={"command": "mailcortex inbox $(touch stolen)"}, session="wrong")

    def test_only_latest_swing_can_unlock(self):
        self.hole["swings"].append({"speaker": "hermes-agent", "session_id": "newer", "lie": None})
        self.save()
        self.refused()

    def test_duplicate_current_claims_refused(self):
        other = dict(self.hole, id="second-hole")
        self.holepath.with_name("second-hole.json").write_text(json.dumps(other))
        self.refused()

    def test_recovery_rejects_foreign_session_claim(self):
        command = (str(m.REPO / "FORGE/bin/prompt-golf") + " record-swing --hole test-hole "
                   "--speaker hermes-agent --session-id wrong --aimed repair")
        self.refused(tool="terminal", args={"command": command}, session="unknown")

    def test_recovery_accepts_this_session_claim(self):
        command = (str(m.REPO / "FORGE/bin/prompt-golf") + " record-swing --hole test-hole "
                   "--speaker hermes-agent --session-id s2 --aimed repair")
        self.assertTrue(self.invoke(tool="terminal", args={"command": command}, session="s2").get("ran"))

    def test_middleware_chain_refuses_without_next(self):
        self.chain(session="wrong")
        self.assertEqual(0, self.called)

    def test_middleware_chain_allows_claimed_once(self):
        self.assertTrue(self.chain(session="s1").get("ran"))
        self.assertEqual(1, self.called)

    def test_middleware_chain_contains_callback_failure(self):
        with patch.object(m, "_claim", side_effect=OSError("fixture failure")):
            result = self.chain(session="s1")
        self.assertEqual(0, self.called)
        self.assertIn("error", result)

    def chain(self, session):
        import sys
        import types
        source = os.environ.get("HERMES_SOURCE")
        if not source:
            self.skipTest("set HERMES_SOURCE to exercise the installed Hermes middleware chain")
        sys.path.insert(0, source)
        self.addCleanup(sys.path.remove, source)
        from hermes_cli.middleware import run_tool_execution_middleware
        import hermes_cli.plugins as plugins
        manager = types.SimpleNamespace(_middleware={"tool_execution": [m.gate]})
        with patch.object(plugins, "_delivery_manager", return_value=manager):
            return run_tool_execution_middleware("write_file", {"path": str(self.wt / "file")},
                                                 self.next, session_id=session)

    def test_registers_both_hooks(self):
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
# test-hermes-protocol-gate ends here
