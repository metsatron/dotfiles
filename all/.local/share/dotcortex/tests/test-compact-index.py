#!/usr/bin/env python3
"""The reader behind a compaction pointer: find, show by line, key and group.

Run: python3 test-compact-index.py
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
MODULE = ROOT / "all/.local/lib/dotcortex/offline_compact.py"
CLI = ROOT / "all/.local/bin/claude-compact-index"


def load():
    loader = importlib.machinery.SourceFileLoader("offline_compact_idx", str(MODULE))
    spec = importlib.util.spec_from_loader("offline_compact_idx", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["offline_compact_idx"] = module
    loader.exec_module(module)
    return module


oc = load()
NEEDLE = "zebrafish-needle"
BIG = NEEDLE + " " + ("tool output line\n" * 400)


def record(kind, role, content, parent):
    return {
        "type": kind,
        "uuid": str(uuid.uuid4()),
        "parentUuid": parent,
        "message": {"role": role, "content": content},
    }


def chain(blank_first=False):
    rows, parent = [], None
    for index in range(10):
        role = "user" if index % 2 == 0 else "assistant"
        if index == 2:
            content = [{"type": "tool_result", "tool_use_id": "t1", "content": BIG}]
        else:
            content = [{"type": "text", "text": "turn %d " % index + "w" * 500}]
        rows.append(record(role, role, content, parent))
        parent = rows[-1]["uuid"]
    return rows


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def compact(self, rows, blank_first=False, group_pointers=False):
        source = self.dir / "source.jsonl"
        text = "".join(json.dumps(row) + "\n" for row in rows)
        source.write_text(("\n" if blank_first else "") + text, encoding="utf-8")
        out = self.dir / "compacted.jsonl"
        archive = self.dir / "archive"
        result = oc.compact(
            source, out, archive,
            ceiling_tokens=3000, harness={"harness_tokens": 1000},
            keep_recent_records=2, stub_over_chars=300, fold_prose=True,
            group_pointers=group_pointers, pointer_source=str(source),
        )
        self.assertTrue(result.ok, result.reason)
        self.assertGreaterEqual(result.report["elided_blocks"], 1)
        return source, archive

    def run_cli(self, *args):
        env = dict(os.environ, DOTCORTEX_COMPACTION_STATE=str(self.dir / "state"))
        return subprocess.run(
            [sys.executable, "-I", str(CLI), *args], capture_output=True, text=True, env=env
        )

    def test_find_returns_the_block_by_a_word_it_contains(self):
        _, archive = self.compact(chain())
        done = self.run_cli("--archive", str(archive), "find", NEEDLE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("r2-0", done.stdout)

    def test_show_by_line_returns_exactly_the_elided_text(self):
        _, archive = self.compact(chain())
        done = self.run_cli("--archive", str(archive), "show", "--line", "3")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, BIG)

    def test_show_by_line_survives_a_blank_line_before_the_record(self):
        _, archive = self.compact(chain(), blank_first=True)
        done = self.run_cli("--archive", str(archive), "show", "--line", "4")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, BIG)

    def test_show_by_key_and_unknown_key(self):
        _, archive = self.compact(chain())
        good = self.run_cli("--archive", str(archive), "show", "--key", "r2-0")
        self.assertEqual(good.stdout, BIG)
        missing = self.run_cli("--archive", str(archive), "show", "--key", "r99-0")
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(missing.stdout, "")

    def test_a_tampered_archive_is_reported_not_returned(self):
        _, archive = self.compact(chain())
        connection = sqlite3.connect(str(archive / "index" / "elided.sqlite3"))
        connection.execute("UPDATE elided SET body = 'forged' WHERE key = 'r2-0'")
        connection.commit()
        connection.close()
        done = self.run_cli("--archive", str(archive), "show", "--key", "r2-0")
        self.assertEqual(done.returncode, 3)
        self.assertNotIn("forged", done.stdout)

    def test_seat_resolves_the_newest_archive(self):
        _, archive = self.compact(chain())
        stamp = self.dir / "state" / "auryn" / "20261126T000000"
        stamp.parent.mkdir(parents=True)
        os.symlink(archive.parent, stamp)
        done = self.run_cli("--seat", "auryn", "show", "--line", "3")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, BIG)

    def test_the_reader_never_writes_to_the_archive(self):
        _, archive = self.compact(chain())
        before = sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in archive.iterdir())
        self.run_cli("--archive", str(archive), "find", NEEDLE)
        self.run_cli("--archive", str(archive), "show", "--line", "3")
        after = sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in archive.iterdir())
        self.assertEqual(before, after)

    def test_a_hyphenated_word_is_a_word_not_a_column_filter(self):
        _, archive = self.compact(chain())
        done = self.run_cli("--archive", str(archive), "find", "zebrafish-needle")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("r2-0", done.stdout)

    def test_a_bad_raw_search_expression_is_a_usage_error_not_a_crash(self):
        _, archive = self.compact(chain())
        done = self.run_cli("--archive", str(archive), "find", "--raw", 'unterminated "quote')
        self.assertEqual(done.returncode, 2)
        self.assertIn("quote", done.stderr)


if __name__ == "__main__":
    unittest.main()
