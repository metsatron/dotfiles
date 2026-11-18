#!/usr/bin/env python3
"""Tests for grouped pointer stubs -- pointers to an index of pointers.

Two behaviours are required by the operator (Telegram, 2026-11-18):

  * a run of elided blocks that belongs to one task may be replaced by ONE stub
    that points at a group in the index, but only when that is genuinely cheaper
    than the individual pointers it replaces;
  * a group stub must carry a summary of the collection, grouped by task and
    project -- a group pointer nobody can read is worse than the text it replaced.

Nothing here forks a process or touches a real session: every path is under a
temporary directory.

Run: python3 test-offline-compact-groups.py
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
MODULE = ROOT / "all/.local/lib/dotcortex/offline_compact.py"

HARNESS = {"harness_tokens": 1000, "harness_family": "claude", "harness_scope": "helmcortex"}
HUGE_CEILING = 10**9


def load_module():
    spec = importlib.util.spec_from_file_location("offline_compact_groups", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


oc = load_module()


def build_task_transcript(path: Path, tasks: int = 2, blocks: int = 12, tool_chars: int = 20_000) -> list[dict]:
    """A transcript where each task is one human instruction plus big tool output."""
    rows: list[dict] = []
    previous = None
    for task in range(tasks):
        instruction = "task %d: fix the cold boundary in module %d" % (task + 1, task + 1)
        for index in range(blocks + 1):
            uid = str(uuid.uuid4())
            if index == 0:
                row = {
                    "type": "user",
                    "uuid": uid,
                    "parentUuid": previous,
                    "sessionId": str(uuid.uuid4()),
                    "message": {"role": "user", "content": [{"type": "text", "text": instruction}]},
                }
            else:
                body = "first line of output %d-%d in /home/metsatron/project/module%d.py\n" % (
                    task + 1,
                    index,
                    task + 1,
                ) + "x" * tool_chars
                row = {
                    "type": "assistant",
                    "uuid": uid,
                    "parentUuid": previous,
                    "sessionId": str(uuid.uuid4()),
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "toolu_%d_%d" % (task, index),
                                "content": body,
                            }
                        ],
                    },
                }
            rows.append(row)
            previous = uid
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return rows


class GroupedPointerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "source.jsonl"
        build_task_transcript(self.source)

    def run_compact(self, **kwargs):
        options = dict(
            out=self.base / "out.jsonl",
            archive_dir=self.base / "archive",
            keep_recent_records=0,
            ceiling_tokens=40_000,
            harness=HARNESS,
            ranker=None,
            group_pointers=True,
        )
        options.update(kwargs)
        if Path(options["out"]).exists():
            Path(options["out"]).unlink()
        return oc.compact(self.source, **options)

    # -- behaviour 1: group only when the pointers take too much space -------

    def test_group_stubs_replace_individual_pointers_when_they_save_space(self):
        result = self.run_compact(group_min_saving_chars=1)
        self.assertTrue(result.ok, result.reason)
        report = result.report
        self.assertGreater(report["pointer_groups"], 0)
        self.assertGreater(report["pointer_group_blocks"], 0)
        self.assertGreater(report["pointer_group_saved_chars"], 0)
        text = (self.base / "out.jsonl").read_text(encoding="utf-8")
        self.assertIn("; group g01 of ", text)
        # Every elided block still names a line of the retained transcript.
        self.assertEqual(report["pointers_verified"], report["pointer_stubs"])
        self.assertEqual(report["pointer_mismatch_count"], 0)

    def test_no_group_when_collapsing_would_not_save_enough(self):
        result = self.run_compact(group_min_saving_chars=10**9)
        self.assertTrue(result.ok, result.reason)
        report = result.report
        self.assertEqual(report["pointer_groups"], 0)
        self.assertEqual(report["pointer_group_blocks"], 0)
        text = (self.base / "out.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("; group g", text)
        self.assertIn("full text retained", text)

    def test_grouping_is_off_by_default(self):
        result = self.run_compact(group_pointers=False)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.report["pointer_groups"], 0)
        text = (self.base / "out.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("; group g", text)

    # -- behaviour 2: a group must be described by task and project ----------

    def test_each_group_carries_a_task_label_and_a_summary(self):
        result = self.run_compact(group_min_saving_chars=1, project="HelmCortex")
        self.assertTrue(result.ok, result.reason)
        details = result.report["pointer_groups_detail"]
        self.assertTrue(details)
        for group in details:
            self.assertTrue(group["label"].startswith("task "), group["label"])
            self.assertIn("blocks,", group["summary"])
            self.assertIn("files:", group["summary"])
            self.assertEqual(group["project"], "HelmCortex")
        text = (self.base / "out.jsonl").read_text(encoding="utf-8")
        # The summary travels with the stub, not only in the report.
        self.assertIn("files: /home/metsatron/project/module1.py", text)

    def test_group_without_a_summary_is_never_created(self):
        rows = oc.load_records_with_lines(self.source)
        candidates = oc.elidable_candidates([record for _n, record in rows], 0, 400)
        texts = {"r%d-0" % n: "text" for n in range(0, 40)}
        groups, _plan = oc.build_pointer_groups(
            rows, candidates, texts=texts, pointer_name=str(self.source), min_saving_chars=1
        )
        self.assertTrue(groups)
        for group in groups:
            self.assertTrue(group["summary"].strip(), "a bare group stub was created")
            self.assertIn("blocks,", group["summary"])

        # A summariser that produces nothing must yield no group at all.
        original = oc._group_summary
        oc._group_summary = lambda count, chars, members, texts: ""
        try:
            groups, plan = oc.build_pointer_groups(
                rows, candidates, texts=texts, pointer_name=str(self.source), min_saving_chars=1
            )
        finally:
            oc._group_summary = original
        self.assertEqual(groups, [])
        self.assertEqual(plan, {})

    # -- the promise a group stub makes -------------------------------------

    def test_group_stub_expands_through_the_index(self):
        result = self.run_compact(group_min_saving_chars=1)
        self.assertTrue(result.ok, result.reason)
        database = Path(result.report["index_path"]) / "elided.sqlite3"
        connection = sqlite3.connect(str(database))
        self.addCleanup(connection.close)
        row = connection.execute(
            "SELECT blocks, summary FROM pointer_groups WHERE gid = ?", ("g01",)
        ).fetchone()
        self.assertIsNotNone(row, "group stub names a group the index does not have")
        blocks, summary = row
        self.assertGreater(blocks, 0)
        self.assertIn("blocks,", summary)
        members = connection.execute(
            "SELECT key FROM pointer_group_members WHERE gid = ?", ("g01",)
        ).fetchall()
        self.assertEqual(len(members), blocks)
        for (key,) in members:
            hit = connection.execute("SELECT 1 FROM elided WHERE key = ?", (key,)).fetchone()
            self.assertIsNotNone(hit, "group member %s is not in the elided index" % key)

    def test_missing_group_in_index_is_a_mismatch(self):
        result = self.run_compact(group_min_saving_chars=1)
        index = oc.ElisionIndex(Path(result.report["index_path"]))
        self.addCleanup(index.close)
        mismatches = oc.verify_groups(
            index,
            [{"gid": "g99", "members": [{"key": "r0-0"}]}],
        )
        self.assertEqual(mismatches[0]["reason"], "group-missing")

    def test_group_mismatch_refuses_to_ship(self):
        original = oc.verify_groups
        oc.verify_groups = lambda index, groups: [{"gid": "g01", "reason": "member-set-mismatch"}]
        try:
            result = self.run_compact(group_min_saving_chars=1)
        finally:
            oc.verify_groups = original
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "group-mismatch")
        self.assertFalse((self.base / "out.jsonl").exists(), "a lying group stub was shipped")


if __name__ == "__main__":
    unittest.main(verbosity=2)
