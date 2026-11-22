#!/usr/bin/env python3
"""Orphan-tolerant chain, context-only accounting, string-content folding.

Each test is built from the real 17 Nov 4d8d0ba3 failure shapes: a trailing
orphan fragment, logging-mod records that carry a message, and whole-string
records (native summaries and channel messages).

Run: python3 test-offline-compact-context.py
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

MODULE = Path(__file__).resolve().parents[5] / "all/.local/lib/dotcortex/offline_compact.py"
SUMMARY_HEAD = "This session is being continued from a previous conversation that ran out of context. "
SUMMARY = SUMMARY_HEAD + "x" * 3000
OLD_SUMMARY = SUMMARY_HEAD + "o" * 3000


def load():
    loader = importlib.machinery.SourceFileLoader("offline_compact_ctx", str(MODULE))
    spec = importlib.util.spec_from_loader("offline_compact_ctx", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["offline_compact_ctx"] = module
    loader.exec_module(module)
    return module


oc = load()


def record(kind, role, content, parent, **extra):
    row = {
        "type": kind,
        "uuid": str(uuid.uuid4()),
        "parentUuid": parent,
        "message": {"role": role, "content": content},
    }
    row.update(extra)
    return row


def chain_rows(older_summary=False, newest_summary=True, length=12):
    rows = []
    parent = None
    if older_summary:
        rows.append(record("user", "user", OLD_SUMMARY, parent))
        parent = rows[-1]["uuid"]
    if newest_summary:
        rows.append(record("user", "user", SUMMARY, parent))
        parent = rows[-1]["uuid"]
    for index in range(length):
        role = "user" if index % 2 == 0 else "assistant"
        rows.append(record(role, role, [{"type": "text", "text": "turn %d " % index + "w" * 500}], parent))
        parent = rows[-1]["uuid"]
    return rows


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    runs = 0

    def run_compact(self, rows, **kwargs):
        self.runs += 1
        source = self.dir / "src{}.jsonl".format(self.runs)
        source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        out = self.dir / "out{}.jsonl".format(self.runs)
        archive = self.dir / "arch{}".format(self.runs)
        # A small ceiling forces elision: the engine only folds what it must.
        params = dict(
            ceiling_tokens=1500,
            harness={"harness_tokens": 1000},
            keep_recent_records=2,
            stub_over_chars=300,
            fold_prose=True,
            group_pointers=False,
            pointer_source=str(source),
        )
        params.update(kwargs)
        result = oc.compact(source, out, archive, **params)
        written = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()] if out.exists() else []
        return result, written

    def test_trailing_orphan_is_reported_excluded_and_chain_unchanged(self):
        rows = chain_rows()
        real = len(rows)
        rows.append(record("user", "user", "orphan one", "does-not-exist"))
        rows.append(record("system", None, "orphan two", "does-not-exist"))
        result, written = self.run_compact(rows)
        report = result.report
        self.assertEqual(report["chain_length"], real)
        self.assertEqual(report["chain_length_after"], real)
        self.assertEqual(report["orphan_count"], 2)
        self.assertTrue(all(item["excluded"] for item in report["orphans_excluded"]))
        self.assertEqual({item["parentUuid"] for item in report["orphans_excluded"]}, {"does-not-exist"})
        self.assertEqual(len(written), real)
        self.assertNotIn("orphan one", json.dumps(written))

    def test_no_complete_chain_is_still_refused(self):
        rows = [record("user", "user", "a", "missing-1"), record("assistant", "assistant", "b", "missing-2")]
        result, _ = self.run_compact(rows)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "chain-broken-before")

    def test_source_with_a_healthy_chain_reports_no_orphans(self):
        result, _ = self.run_compact(chain_rows())
        self.assertEqual(result.report["orphan_count"], 0)

    def test_logging_records_are_not_counted_and_carry_no_stub(self):
        rows = chain_rows()
        blob = record("api-request-blob", "user", "B" * 200_000, None)
        blob.pop("uuid")
        rows.insert(3, blob)
        plain, _ = self.run_compact(chain_rows())
        mixed, written = self.run_compact(rows)
        self.assertEqual(mixed.report["est_tokens_before"], plain.report["est_tokens_before"])
        self.assertEqual(mixed.report["non_context_records_excluded"], 1)
        self.assertEqual(mixed.report["index_unreadable_records"], [])
        blobs = [row for row in written if row.get("type") == "api-request-blob"]
        self.assertEqual(blobs[0]["message"]["content"], "B" * 200_000)

    def test_whole_string_record_folds_byte_exact_and_verifies(self):
        rows = chain_rows(newest_summary=False)
        big = "channel text " * 80
        rows.insert(2, record("user", "user", big, rows[1]["uuid"]))
        rows[3]["parentUuid"] = rows[2]["uuid"]
        result, written = self.run_compact(rows)
        report = result.report
        self.assertGreaterEqual(report["elided_blocks"], 1)
        self.assertEqual(report["pointer_mismatch_count"], 0)
        self.assertEqual(report["human_relocation_missing"], [])
        folded = [row for row in written if isinstance(row["message"]["content"], str) and "elided" in row["message"]["content"]]
        self.assertTrue(folded)
        self.assertNotIn(big, json.dumps(written))

    def test_newest_summary_stays_verbatim_and_older_one_folds(self):
        rows = chain_rows(older_summary=True, newest_summary=True)
        result, written = self.run_compact(rows)
        texts = [row["message"]["content"] for row in written if isinstance(row["message"]["content"], str)]
        self.assertIn(SUMMARY, texts)
        self.assertNotIn(OLD_SUMMARY, texts)
        self.assertEqual(result.report["pinned_summary_position"], 1)

    def test_a_logging_copy_of_the_summary_is_never_the_pinned_one(self):
        rows = chain_rows(newest_summary=True)
        copy = record("api-request-blob", "user", SUMMARY, None)
        copy.pop("uuid")
        rows.append(copy)
        result, _ = self.run_compact(rows)
        self.assertEqual(result.report["pinned_summary_position"], 0)


if __name__ == "__main__":
    unittest.main()
