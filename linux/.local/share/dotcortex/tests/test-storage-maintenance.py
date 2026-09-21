#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
CLEANUP = ROOT / "all/.local/bin/dotcortex-storage-maintenance"
INSTALLER = ROOT / "linux/.local/bin/dotcortex-storage-maintenance-cron-apply"


class StorageMaintenanceTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict[str, str], Path, Path, Path]:
        fake_guix = root / "guix"
        dead = root / "dead-store-item"
        dead.mkdir()
        (dead / "payload").write_bytes(b"x" * 4096)
        marker = root / "guix-gc-ran"
        fake_guix.write_text(
            "#!/bin/sh\n"
            f"if [ \"$*\" = 'gc --list-dead' ]; then printf '%s\\n' '{dead}'; exit 0; fi\n"
            f"if [ \"$*\" = 'gc' ]; then : >'{marker}'; "
            "printf '%s\\n' detail-1 detail-2 detail-3 summary-1 summary-2; exit 0; fi\n"
            "exit 2\n",
            encoding="utf-8",
        )
        fake_guix.chmod(0o755)

        runaway = root / ".local/share/dotcortex/guests/test/home/.cache/redstone-9x/clipmenud.log"
        runaway.parent.mkdir(parents=True)
        with runaway.open("wb") as handle:
            handle.truncate(17 * 1024 * 1024)

        candidates = root / ".cache/ductor-candidates"
        old = candidates / "old"
        fresh = candidates / "fresh"
        old.mkdir(parents=True)
        fresh.mkdir()
        old_time = time.time() - (20 * 86400)
        os.utime(old, (old_time, old_time))

        unrelated = root / ".cache/must-survive"
        unrelated.write_text("keeper", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "STORAGE_MAINTENANCE_HOME": str(root),
                "STORAGE_MAINTENANCE_HOSTNAME": "kikin-kushi",
                "STORAGE_MAINTENANCE_GUIX": str(fake_guix),
            }
        )
        return env, marker, runaway, old

    def test_help(self) -> None:
        result = subprocess.run([CLEANUP, "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("narrow DotCortex cleanup allowlist", result.stdout)

    def test_host_guard(self) -> None:
        env = os.environ.copy()
        env["STORAGE_MAINTENANCE_HOSTNAME"] = "not-kikin"
        result = subprocess.run(
            [CLEANUP, "--expected-host", "kikin-kushi", "--dry-run"],
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing", result.stderr)

    def test_dry_run_is_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env, marker, runaway, old = self.fixture(root)
            result = subprocess.run(
                [CLEANUP, "--expected-host", "kikin-kushi", "--dry-run"],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(runaway.stat().st_size, 17 * 1024 * 1024)
            self.assertTrue(old.exists())
            self.assertIn("would truncate", result.stdout)
            self.assertIn("would remove", result.stdout)

    def test_real_run_changes_only_allowlisted_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env, marker, runaway, old = self.fixture(root)
            result = subprocess.run(
                [CLEANUP, "--expected-host", "kikin-kushi"],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists())
            self.assertEqual(runaway.stat().st_size, 0)
            self.assertFalse(old.exists())
            self.assertTrue((root / ".cache/ductor-candidates/fresh").exists())
            self.assertEqual((root / ".cache/must-survive").read_text(), "keeper")
            self.assertNotIn("detail-1", result.stdout)
            self.assertIn("summary-2", result.stdout)

    def test_cron_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = os.environ.copy()
            env.update(
                {
                    "STORAGE_MAINTENANCE_HOME": str(root),
                    "STORAGE_MAINTENANCE_HOSTNAME": "kikin-kushi",
                    "STORAGE_MAINTENANCE_USER": "test-user",
                    "STORAGE_MAINTENANCE_UID": "1234",
                }
            )
            result = subprocess.run(
                [INSTALLER, "--host", "kikin-kushi", "--dry-run"],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("30 6 * * * test-user", result.stdout)
            self.assertIn("--expected-host kikin-kushi", result.stdout)
            self.assertIn(str(root / ".local/state/dotcortex-storage-maintenance/cron.log"), result.stdout)


if __name__ == "__main__":
    unittest.main()
