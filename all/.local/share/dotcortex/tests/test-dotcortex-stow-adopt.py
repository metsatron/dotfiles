#!/usr/bin/env python3
"""Tests for dotcortex-stow-adopt and the safe-stow STOW_CONFLICTS policy (layers.org)."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
HELPER = ROOT / "all/.local/bin/dotcortex-stow-adopt"


class Box:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo, self.home, self.skel = base / "repo", base / "home", base / "skel"
        for rel, text in {"all/.bashrc": "dotcortex bashrc\n", "all/.config/app/conf": "dc conf\n",
                          "all/.local/bin/tool": "tool v1\n", "honey/.local/bin/honey-x": "x\n"}.items():
            self.write(self.repo / rel, text)
        self.write(self.skel / ".bashrc", "skel bashrc\n")
        self.write(self.skel / ".config/app/conf", "skel conf\n")

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run(self, *args):
        cmd = [sys.executable, str(HELPER), "--dir", str(self.repo), "--target", str(self.home),
               "--packages", "all honey", "--skel", str(self.skel), *args]
        return subprocess.run(cmd, capture_output=True, text=True)

    def stow(self):
        return subprocess.run(["stow", "-d", str(self.repo), "-t", str(self.home), "all", "honey"],
                              capture_output=True, text=True)

    def close(self):
        self.tmp.cleanup()


class AdoptTests(unittest.TestCase):
    def setUp(self):
        self.box = Box()
        self.addCleanup(self.box.close)
        b = self.box
        b.write(b.home / ".bashrc", "skel bashrc\n")             # untouched useradd default
        b.write(b.home / ".local/bin/tool", "tool v1\n")          # identical to the package

    def test_fresh_account_is_adopted_and_stows(self):
        b = self.box
        dry = b.run()
        self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
        self.assertIn("skel       .bashrc", dry.stdout)
        self.assertIn("identical  .local/bin/tool", dry.stdout)
        self.assertEqual((b.home / ".bashrc").read_text(), "skel bashrc\n", "dry-run changed the home")
        state = Path(b.tmp.name) / "state"
        applied = b.run("--apply", "--state", str(state))
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertEqual((state / "skel/.bashrc").read_text(), "skel bashrc\n")
        self.assertIn("skel\t.bashrc", (state / "manifest.tsv").read_text())
        self.assertEqual(b.stow().returncode, 0)
        self.assertTrue((b.home / ".bashrc").is_symlink())
        subprocess.run(["stow", "-D", "-d", str(b.repo), "-t", str(b.home), "all", "honey"], check=True)
        subprocess.run(["sh", str(state / "restore.sh")], check=True)
        self.assertEqual((b.home / ".bashrc").read_text(), "skel bashrc\n")
        self.assertEqual((b.home / ".local/bin/tool").read_text(), "tool v1\n")

    def test_edited_config_stops_and_changes_nothing(self):
        b = self.box
        b.write(b.home / ".config/app/conf", "my own edits\n")
        before = {p: p.read_text() for p in b.home.rglob("*") if p.is_file()}
        result = b.run("--apply", "--state", str(Path(b.tmp.name) / "state"))
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("keep       .config/app/conf", result.stdout)
        self.assertIn("STOP", result.stdout)
        self.assertEqual({p: p.read_text() for p in b.home.rglob("*") if p.is_file()}, before)
        self.assertFalse((Path(b.tmp.name) / "state").exists())

    def test_foreign_symlink_stops(self):
        b = self.box
        (b.home / ".config/app").mkdir(parents=True)
        os.symlink("/nonexistent", b.home / ".config/app/conf")
        result = b.run()
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("keep", result.stdout)

    def test_a_stow_error_is_a_stop_not_a_pass(self):
        b = self.box
        result = subprocess.run([sys.executable, str(HELPER), "--dir", str(b.repo), "--target", str(b.home),
                                 "--packages", "all no-such-package", "--skel", str(b.skel)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("stow failed", result.stdout)

    def test_clean_home_has_nothing_to_adopt(self):
        b = self.box
        for rel in (".bashrc", ".local/bin/tool"):
            (b.home / rel).unlink()
        result = b.run("--apply")
        self.assertEqual(result.returncode, 0)
        self.assertIn("nothing to adopt", result.stdout)


class SafeStowPolicyTests(unittest.TestCase):
    def test_policy_is_opt_in_and_runs_before_the_legacy_backup(self):
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("STOW_CONFLICTS ?= backup", makefile)
        recipe = makefile.split("\nsafe-stow:", 1)[1]
        adopt = recipe.index("dotcortex-stow-adopt")
        legacy = recipe.index('cp -a "$$abs" "$$abs.bak.$$ts"')
        self.assertLess(adopt, legacy)
        self.assertIn('"$(STOW_CONFLICTS)" = adopt', recipe)


if __name__ == "__main__":
    unittest.main()
