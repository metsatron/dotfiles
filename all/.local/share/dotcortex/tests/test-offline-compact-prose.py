#!/usr/bin/env python3
"""Tests for folding OLDER PROSE into pointers, not only tool output.

The gap these close (Telegram, 2026-11-19): eliding tool output alone cannot bring
a long session under the cold-reload ceiling, because the prose is the payload.
So an old human or assistant turn -- and an old tool call's arguments -- may leave
the working copy, but only as a pointer to the exact line of the retained
transcript, with the text byte-exact in the index.  The recent tail stays verbatim.

Run: python3 test-offline-compact-prose.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
MODULE = ROOT / "all/.local/lib/dotcortex/offline_compact.py"
MODULE_PATH = MODULE

HARNESS = {"harness_tokens": 1000, "harness_family": "claude", "harness_scope": "helmcortex"}


def load_module():
    spec = importlib.util.spec_from_file_location("offline_compact_prose", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


oc = load_module()


def build_prose_transcript(path: Path, turns: int = 20, chars: int = 6000, tail: int = 4) -> list[dict]:
    """Prose-heavy transcript: every turn carries a long human and assistant text."""
    rows: list[dict] = []
    previous = None
    for index in range(turns):
        for role in ("user", "assistant"):
            uid = str(uuid.uuid4())
            text = "%s turn %d: %s" % (role, index, "prose " * (chars // 6))
            row = {
                "type": role,
                "uuid": uid,
                "parentUuid": previous,
                "sessionId": str(uuid.uuid4()),
                "message": {"role": role, "content": [{"type": "text", "text": text}]},
            }
            rows.append(row)
            previous = uid
        # a tool call with bulky arguments, then its result
        uid = str(uuid.uuid4())
        rows.append(
            {
                "type": "assistant",
                "uuid": uid,
                "parentUuid": previous,
                "sessionId": str(uuid.uuid4()),
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_%d" % index,
                            "name": "Read",
                            "input": {"path": "/home/metsatron/x%d.py" % index, "blob": "z" * 3000},
                        }
                    ],
                },
            }
        )
        previous = uid
        uid = str(uuid.uuid4())
        rows.append(
            {
                "type": "user",
                "uuid": uid,
                "parentUuid": previous,
                "sessionId": str(uuid.uuid4()),
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_%d" % index,
                            "content": "result %d\n" % index + "r" * 2000,
                        }
                    ],
                },
            }
        )
        previous = uid
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return rows


class ProseFoldingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "source.jsonl"
        self.rows = build_prose_transcript(self.source)

    def run_compact(self, **kwargs):
        options = dict(
            out=self.base / "out.jsonl",
            archive_dir=self.base / "archive",
            keep_recent_records=4,
            ceiling_tokens=12_000,
            harness=HARNESS,
            ranker=None,
            group_pointers=False,
        )
        options.update(kwargs)
        if Path(options["out"]).exists():
            Path(options["out"]).unlink()
        return oc.compact(self.source, **options)

    def test_prose_is_untouched_by_default(self):
        result = self.run_compact(fold_prose=False)
        self.assertEqual(result.report["prose_blocks_folded"], 0)
        self.assertEqual(result.report["human_blocks_relocated"], 0)
        text = (self.base / "out.jsonl").read_text(encoding="utf-8")
        self.assertIn("prose ", text)

    def test_older_prose_folds_to_a_pointer_into_the_transcript(self):
        result = self.run_compact(fold_prose=True)
        self.assertTrue(result.ok, result.reason)
        report = result.report
        self.assertGreater(report["prose_blocks_folded"], 0)
        self.assertGreater(report["human_blocks_relocated"], 0)
        self.assertEqual(report["pointer_mismatch_count"], 0)
        rows = [json.loads(line) for line in (self.base / "out.jsonl").read_text().splitlines()]
        pointers = [
            part["text"]
            for row in rows
            for part in (row.get("message") or {}).get("content") or []
            if isinstance(part, dict) and part.get("type") == "text" and "at line " in part.get("text", "")
        ]
        self.assertTrue(pointers, "no prose block was folded to a pointer")
        self.assertIn("full text retained", pointers[0])
        self.assertIn(str(self.source), pointers[0])

    def test_folded_human_words_are_byte_exact_in_the_index(self):
        result = self.run_compact(fold_prose=True)
        self.assertTrue(result.ok, result.reason)
        original = {}
        for number, row in enumerate(self.rows, start=1):
            for block_index, part in enumerate((row.get("message") or {}).get("content") or []):
                if isinstance(part, dict) and part.get("type") == "text":
                    original["r%d-%d" % (number - 1, block_index)] = part["text"]
        index = oc.ElisionIndex(Path(result.report["index_path"]))
        self.addCleanup(index.close)
        checked = 0
        for key, text in original.items():
            stored = index.body(key)
            if stored is None:
                continue
            self.assertEqual(stored, text, "an indexed pointer does not hold the words it replaced")
            checked += 1
        self.assertGreater(checked, 0)
        self.assertEqual(result.report["human_relocation_missing"], [])

    def test_recent_tail_stays_verbatim(self):
        result = self.run_compact(fold_prose=True)
        self.assertTrue(result.ok, result.reason)
        rows = [json.loads(line) for line in (self.base / "out.jsonl").read_text().splitlines()]
        tail_text = json.dumps(rows[-4:])
        self.assertIn("prose ", tail_text)
        self.assertNotIn("at line ", tail_text)

    def test_tool_call_stays_structurally_valid_when_its_arguments_fold(self):
        result = self.run_compact(fold_prose=True)
        self.assertTrue(result.ok, result.reason)
        rows = [json.loads(line) for line in (self.base / "out.jsonl").read_text().splitlines()]
        calls = [
            part
            for row in rows
            for part in (row.get("message") or {}).get("content") or []
            if isinstance(part, dict) and part.get("type") == "tool_use"
        ]
        self.assertTrue(calls)
        folded = [call for call in calls if "_elided_pointer" in (call.get("input") or {})]
        self.assertTrue(folded, "bulky tool arguments were never folded")
        for call in folded:
            self.assertIsInstance(call["input"], dict)
            self.assertIn("full text retained", call["input"]["_elided_pointer"])

    def test_a_lost_human_block_refuses_to_ship(self):
        original = oc.ElisionIndex.body
        oc.ElisionIndex.body = lambda self, key: None
        try:
            result = self.run_compact(fold_prose=True)
        finally:
            oc.ElisionIndex.body = original
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "human-words-changed")
        self.assertFalse((self.base / "out.jsonl").exists())

    def test_prose_folding_is_what_meets_the_ceiling(self):
        # Tool output alone cannot meet this ceiling; the prose is the payload.
        without = self.run_compact(fold_prose=False, ceiling_tokens=12_000)
        self.assertFalse(without.ok)
        self.assertEqual(without.reason, "ceiling-not-met")
        with_prose = self.run_compact(fold_prose=True, ceiling_tokens=12_000)
        self.assertTrue(with_prose.ok, with_prose.reason)
        self.assertLess(
            with_prose.report["est_tokens_after"],
            without.report["est_tokens_after"],
            "folding prose did not reduce the working context",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
