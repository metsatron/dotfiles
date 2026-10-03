#!/usr/bin/env python3
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[3] / "bin" / "dotcortex-safe-commit"


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=check).stdout.strip()


class SafeCommit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "master")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "core.hooksPath", ".nohooks")
        for name in ("a.txt", "b.txt", "c.txt"):
            (self.repo / name).write_text(name + "\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *paths, env=None):
        return subprocess.run([str(TOOL), "-C", str(self.repo), "-m", "msg", "--", *paths],
                              capture_output=True, text=True, env=env)

    def test_exact_paths_only(self):
        (self.repo / "a.txt").write_text("mine\n")
        (self.repo / "b.txt").write_text("other lane, unstaged\n")
        (self.repo / "c.txt").write_text("other lane, staged\n")
        git(self.repo, "add", "c.txt")
        result = self.run_tool("a.txt")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git(self.repo, "diff-tree", "-r", "--no-commit-id", "--name-only", "HEAD"), "a.txt")
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), "c.txt")
        self.assertEqual(git(self.repo, "diff", "--name-only"), "b.txt")

    def test_deletion(self):
        (self.repo / "b.txt").unlink()
        result = self.run_tool("b.txt")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git(self.repo, "diff-tree", "-r", "--no-commit-id", "--name-status", "HEAD"), "D\tb.txt")

    def test_unchanged_path_refuses(self):
        before = git(self.repo, "rev-parse", "HEAD")
        result = self.run_tool("a.txt")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), before)

    def test_failing_hook_refuses(self):
        hooks = self.repo / ".nohooks"
        hooks.mkdir()
        (hooks / "pre-commit").write_text("#!/bin/sh\nexit 1\n")
        (hooks / "pre-commit").chmod(0o755)
        (self.repo / "a.txt").write_text("mine\n")
        before = git(self.repo, "rev-parse", "HEAD")
        result = self.run_tool("a.txt")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), before)

    def test_concurrent_commit_is_never_reverted(self):
        # The hook commits another lane's change mid-run, moving HEAD.
        hooks = self.repo / ".nohooks"
        hooks.mkdir()
        (hooks / "pre-commit").write_text(
            "#!/bin/sh\nunset GIT_INDEX_FILE\n"
            "echo racer > c.txt && git add c.txt && git -c core.hooksPath=/dev/null commit -qm racer\n")
        (hooks / "pre-commit").chmod(0o755)
        (self.repo / "a.txt").write_text("mine\n")
        result = self.run_tool("a.txt")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s"), "racer")
        self.assertEqual(git(self.repo, "show", "HEAD:c.txt"), "racer")


if __name__ == "__main__":
    unittest.main()
