#!/usr/bin/env python3
# [[file:../../../../../odin.org::*Host adb access: the Android udev rule][Host adb access: the Android udev rule:2]]
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
INSTALLER = ROOT / "linux/.local/bin/android-udev-install"


class AndroidUdevTests(unittest.TestCase):
    def run_installer(self, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(INSTALLER), *args], env=env, text=True, capture_output=True, check=False
        )

    def test_install_check_and_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "51-android.rules"
            env = os.environ.copy()
            env["ANDROID_UDEV_TARGET"] = str(target)
            env["ANDROID_UDEV_USER"] = "root"

            dry = self.run_installer("--dry-run", env=env)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertIn('ATTR{idVendor}=="0e8d"', dry.stdout)
            self.assertFalse(target.exists(), "--dry-run must not write")

            missing = self.run_installer("--check", env=env)
            self.assertEqual(missing.returncode, 1)

            done = self.run_installer(env=env)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), dry.stdout)

            again = self.run_installer(env=env)
            self.assertIn("already installed", again.stdout)

            target.write_text(dry.stdout + "# drift\n", encoding="utf-8")
            drifted = self.run_installer("--check", env=env)
            self.assertEqual(drifted.returncode, 1)
            self.assertIn("drift", drifted.stderr)

    def test_rejects_unknown_flag(self) -> None:
        bad = self.run_installer("--bogus", env=os.environ.copy())
        self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
# Host adb access: the Android udev rule:2 ends here
