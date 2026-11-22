#!/usr/bin/env python3
"""repair_orphan_chain: reconnect a trailing orphan fragment, touch nothing else, refuse the rest.

Shape from the real case (Fable's session 4d8d0ba3, 17 Nov 2026): a 5-hour-limited native
/compact wrote a record whose parentUuid names a uuid no record defines.

Run: python3 test-offline-compact-repair.py
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[5] / "all/.local/lib/dotcortex/offline_compact.py"


def load():
    loader = importlib.machinery.SourceFileLoader("offline_compact_repair", str(MODULE))
    spec = importlib.util.spec_from_loader("offline_compact_repair", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["offline_compact_repair"] = module
    loader.exec_module(module)
    return module


oc = load()


def line(uid, parent, text="x"):
    return json.dumps({"parentUuid": parent, "uuid": uid, "type": "user", "message": {"role": "user", "content": text}}, separators=(",", ":")) + "\n"


def healthy():
    return [line("a", None), line("b", "a"), line("c", "b")]


def with_orphan_fragment():
    # d hangs off a uuid nothing defines; e and f follow d (the post-failed-compact fragment)
    return healthy() + [line("d", "ghost", "caveat"), line("e", "d"), line("f", "e")]


class RepairTests(unittest.TestCase):
    def test_a_whole_chain_is_returned_unchanged_with_no_repairs(self):
        lines = healthy()
        repaired, report = oc.repair_orphan_chain(lines)
        self.assertEqual(repaired, lines)
        self.assertEqual(report, [])

    def test_the_fragment_is_reconnected_to_the_real_tip(self):
        lines = with_orphan_fragment()
        repaired, report = oc.repair_orphan_chain(lines)
        self.assertEqual(len(report), 1)
        self.assertEqual((report[0]["old_parentUuid"], report[0]["new_parentUuid"], report[0]["uuid"]), ("ghost", "c", "d"))
        records = [json.loads(x) for x in repaired]
        self.assertEqual(oc.parent_chain(records), ["f", "e", "d", "c", "b", "a"])

    def test_only_the_one_line_changes_and_only_its_parent(self):
        lines = with_orphan_fragment()
        repaired, _ = oc.repair_orphan_chain(lines)
        changed = [i for i, (a, b) in enumerate(zip(lines, repaired)) if a != b]
        self.assertEqual(changed, [3])
        before, after = json.loads(lines[3]), json.loads(repaired[3])
        after["parentUuid"] = before["parentUuid"]
        self.assertEqual(before, after)

    def test_repairing_twice_is_a_no_op(self):
        once, _ = oc.repair_orphan_chain(with_orphan_fragment())
        twice, report = oc.repair_orphan_chain(once)
        self.assertEqual((twice, report), (once, []))

    def test_a_second_gap_is_refused_and_nothing_is_returned(self):
        lines = with_orphan_fragment() + [line("g", "ghost2"), line("h", "g")]
        # g/h hang off a different missing parent; the fragment has two roots
        with self.assertRaises(oc.ChainError):
            oc.repair_orphan_chain(lines)

    def test_a_parent_text_inside_message_content_is_not_what_gets_rewritten(self):
        # the needle also appears inside the content of the orphan record; the top-level key wins
        text = 'see "parentUuid":"ghost" in the log'
        lines = healthy() + [line("d", "ghost", text), line("e", "d")]
        repaired, report = oc.repair_orphan_chain(lines)
        self.assertEqual(json.loads(repaired[3])["message"]["content"], text)
        self.assertEqual(json.loads(repaired[3])["parentUuid"], "c")

    def test_a_line_not_in_the_compact_form_is_refused_not_guessed_at(self):
        spaced = json.dumps({"parentUuid": "ghost", "uuid": "d", "type": "user", "message": {"role": "user", "content": "x"}}) + "\n"
        self.assertIn('"parentUuid": "ghost"', spaced)
        with self.assertRaises(oc.ChainError):
            oc.repair_orphan_chain(healthy() + [spaced])

    def test_a_rewrite_that_would_hit_a_nested_copy_of_the_key_is_refused(self):
        # a nested {"parentUuid":"ghost"} comes first in the line, so the first textual match is not the record's own
        tricky = '{"meta":{"parentUuid":"ghost"},"parentUuid":"ghost","uuid":"d","type":"user","message":{"role":"user","content":"x"}}\n'
        with self.assertRaises(oc.ChainError):
            oc.repair_orphan_chain(healthy() + [tricky])

    def test_the_file_form_writes_a_copy_and_never_touches_the_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "s.jsonl"
            out = Path(tmp) / "fixed.jsonl"
            source.write_text("".join(with_orphan_fragment()), encoding="utf-8")
            before = source.read_bytes()
            report = oc.repair_orphan_chain_file(source, out)
            self.assertEqual(len(report), 1)
            self.assertEqual(source.read_bytes(), before)
            fixed = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(oc.parent_chain(fixed)[-1], "a")
            self.assertEqual(len(oc.parent_chain(fixed)), 6)

    def test_repair_in_place_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "s.jsonl"
            source.write_text("".join(with_orphan_fragment()), encoding="utf-8")
            with self.assertRaises(oc.ChainError):
                oc.repair_orphan_chain_file(source, source)

    def test_a_whole_file_writes_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "s.jsonl"
            out = Path(tmp) / "fixed.jsonl"
            source.write_text("".join(healthy()), encoding="utf-8")
            self.assertEqual(oc.repair_orphan_chain_file(source, out), [])
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
