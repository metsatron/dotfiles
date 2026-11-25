#!/usr/bin/env python3
"""Ledger attachments are archived, dropped, and the chain closes over them.

Run: python3 test-offline-compact-attachments.py
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


def load():
    loader = importlib.machinery.SourceFileLoader("offline_compact_att", str(MODULE))
    spec = importlib.util.spec_from_loader("offline_compact_att", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["offline_compact_att"] = module
    loader.exec_module(module)
    return module


oc = load()
INSTRUCTIONS = {"type": "instructions", "files": [{"path": "CLAUDE.md", "type": "User", "content": "I" * 6000}]}
SKILLS = {"type": "invoked_skills", "skills": [{"name": "x", "path": "p", "content": "S" * 4000}]}
HOOK = {"type": "hook_success", "hookName": "h", "content": "H" * 3000, "stdout": "H" * 3000}
KEPT = {"type": "queued_command", "prompt": "a human word queued while the model worked"}


def message(role, text, parent):
    return {
        "type": role, "uuid": str(uuid.uuid4()), "parentUuid": parent, "timestamp": "2026-11-26T00:00:00Z",
        "message": {"role": role, "content": [{"type": "text", "text": text}]},
    }


def attachment(payload, parent):
    return {
        "type": "attachment", "uuid": str(uuid.uuid4()), "parentUuid": parent,
        "timestamp": "2026-11-26T00:00:00Z", "attachment": payload,
    }


def chain(with_attachments=True):
    rows, parent = [], None
    plan = [("user", None), ("assistant", INSTRUCTIONS), ("user", SKILLS), ("assistant", HOOK),
            ("user", KEPT), ("assistant", None), ("user", None), ("assistant", None)]
    for index, (role, payload) in enumerate(plan):
        if payload is not None and with_attachments:
            row = attachment(payload, parent)
            rows.append(row)
            parent = row["uuid"]
        row = message(role, "turn %d " % index + "w" * 400, parent)
        rows.append(row)
        parent = row["uuid"]
    return rows


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.runs = 0

    def run_compact(self, rows, **kwargs):
        self.runs += 1
        source = self.dir / "s{}.jsonl".format(self.runs)
        source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        out = self.dir / "o{}.jsonl".format(self.runs)
        archive = self.dir / "a{}".format(self.runs)
        params = dict(
            ceiling_tokens=100000, harness={"harness_tokens": 1000}, keep_recent_records=2,
            stub_over_chars=300, fold_prose=True, group_pointers=False, pointer_source=str(source),
        )
        params.update(kwargs)
        result = oc.compact(source, out, archive, **params)
        written = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()] if out.exists() else []
        return result, written, archive

    def test_ledger_attachments_are_dropped_and_the_chain_closes(self):
        rows = chain()
        result, written, _ = self.run_compact(rows)
        self.assertTrue(result.ok or result.reason == "no-elision-needed", result.reason)
        kinds = [row["attachment"]["type"] for row in written if row["type"] == "attachment"]
        self.assertEqual(kinds, ["queued_command"])
        uuids = {row["uuid"] for row in written}
        for row in written:
            self.assertTrue(row["parentUuid"] is None or row["parentUuid"] in uuids, row["type"])
        self.assertEqual(result.report["attachment_records_dropped"], 3)
        self.assertEqual(result.report["chain_length_after"], len(rows) - 3)
        self.assertTrue(result.report["identity_preserved"])

    def test_every_dropped_attachment_is_in_the_index_byte_exact_before_it_goes(self):
        rows = chain()
        _, _, archive = self.run_compact(rows)
        index = oc.ElisionIndex(archive / "index")
        try:
            for position, row in enumerate(rows):
                if row["type"] == "attachment" and row["attachment"]["type"] != "queued_command":
                    self.assertEqual(index.body("r{}-att".format(position)), json.dumps(row["attachment"]))
        finally:
            index.close()

    def test_the_reload_estimate_counts_attachments(self):
        with_att, _, _ = self.run_compact(chain(), drop_ledger_attachments=False)
        without, _, _ = self.run_compact(chain(with_attachments=False))
        self.assertGreater(with_att.report["est_tokens_before"], without.report["est_tokens_before"] + 3000)
        dropped, _, _ = self.run_compact(chain())
        self.assertLess(dropped.report["est_tokens_after"], with_att.report["est_tokens_after"] - 3000)

    def test_opting_out_keeps_every_attachment(self):
        rows = chain()
        result, written, _ = self.run_compact(rows, drop_ledger_attachments=False)
        self.assertEqual(len(written), len(rows))
        self.assertEqual(result.report["attachment_records_dropped"], 0)

    def test_a_queued_human_word_is_never_dropped(self):
        _, written, _ = self.run_compact(chain())
        kept = [row["attachment"] for row in written if row["type"] == "attachment"]
        self.assertEqual(kept, [KEPT])


if __name__ == "__main__":
    unittest.main()
