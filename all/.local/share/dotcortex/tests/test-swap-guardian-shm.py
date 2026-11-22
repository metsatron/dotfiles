#!/usr/bin/env python3
"""swap-guardian: orphaned SysV shared memory is reported, and reaped only when asked, and only the right ones.

HOME is a temporary directory in every run so the guardian can never call the real herald dispatch."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

GUARDIAN = Path(__file__).resolve().parents[5] / "linux/.local/bin/swap-guardian"
NOW = 1_800_000_000
HEADER = "key shmid perms size cpid lpid nattch uid gid cuid cgid atime dtime ctime rss swap\n"
MIB = 1024 * 1024


def row(shmid, size_mib, nattch, uid, idle_min):
    t = NOW - idle_min * 60
    return f"0 {shmid} 1600 {size_mib * MIB} 100 100 {nattch} {uid} {uid} {uid} {uid} {t} {t} {t} 0 0\n"


class SwapGuardianShmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.me = os.getuid()
        self.removed = self.dir / "removed.txt"
        self.ipcrm = self.dir / "ipcrm"
        self.ipcrm.write_text(f'#!/bin/sh\necho "$2" >> {self.removed}\n')
        self.ipcrm.chmod(0o755)
        self.proc = self.dir / "shm"

    def run_guardian(self, rows, *args):
        self.proc.write_text(HEADER + "".join(rows))
        env = {
            "PATH": os.environ["PATH"], "HOME": str(self.dir), "XDG_STATE_HOME": str(self.dir / "state"),
            "SHM_PROC_FILE": str(self.proc), "SHM_NOW": str(NOW), "IPCRM_BIN": str(self.ipcrm),
        }
        return subprocess.run([str(GUARDIAN), *args], env=env, capture_output=True, text=True, timeout=60)

    def removed_ids(self):
        return self.removed.read_text().split() if self.removed.exists() else []

    ROWS = None

    def mixed(self):
        return [
            row(11, 128, 0, self.me, 120),   # orphan, idle two hours: counts and is reapable
            row(12, 128, 0, self.me, 5),     # orphan but idle only 5 minutes: not yet
            row(13, 128, 2, self.me, 120),   # attached: never
            row(14, 128, 0, self.me + 1, 120),  # another user's orphan: never
        ]

    def test_it_reports_only_the_orphans_that_are_old_enough_and_removes_nothing_by_default(self):
        result = self.run_guardian(self.mixed(), "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("shm-orphans=1 (128MiB)", result.stdout)
        self.run_guardian(self.mixed())  # a real run without --reap-shm
        self.assertEqual(self.removed_ids(), [])

    def test_the_warning_threshold_names_the_leak(self):
        result = self.run_guardian(self.mixed(), "--dry-run", "--shm-warn-mib", "100")
        self.assertIn("SHM: 1 orphaned SysV segment(s), 128MiB (warn at 100MiB)", result.stdout)

    def test_reap_removes_exactly_the_idle_unattached_segments_of_this_user(self):
        result = self.run_guardian(self.mixed(), "--reap-shm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.removed_ids(), ["11"])
        self.assertIn("Reaped 1 orphaned shm segment(s) of 1 found", result.stdout)

    def test_reap_in_dry_run_removes_nothing_and_says_what_it_would_do(self):
        result = self.run_guardian(self.mixed(), "--reap-shm", "--dry-run")
        self.assertEqual(self.removed_ids(), [])
        self.assertIn("[DRY RUN] Would remove orphaned shm segment 11 (128 MiB)", result.stdout)

    def test_no_orphans_is_quiet_and_removes_nothing(self):
        result = self.run_guardian([row(13, 128, 2, self.me, 120)], "--reap-shm", "--dry-run")
        self.assertNotIn("shm-orphans", result.stdout)
        self.assertEqual(self.removed_ids(), [])


if __name__ == "__main__":
    unittest.main()
