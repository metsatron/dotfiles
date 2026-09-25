#!/usr/bin/env python3
from __future__ import annotations

import grp
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
SHARE = ROOT / "all/.local/bin/agent-repo-share"


def snapshot(repo: Path) -> list[tuple[str, int, int]]:
    rows = []
    for p in sorted(repo.rglob("*")) + [repo]:
        st = p.lstat()
        rows.append((str(p.relative_to(repo)), st.st_mode, st.st_gid))
    return rows


@unittest.skipUnless(any(g.gr_name == "cortex" for g in grp.getgrall()), "needs the cortex group")
class AgentRepoShareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        (self.repo / "sub").mkdir(parents=True)
        (self.repo / "sub/a").write_text("a")
        (self.repo / "b").write_text("b")
        (self.repo / "ign").mkdir()
        (self.repo / "ign/x").write_text("x")
        (self.repo / ".gitignore").write_text("ign/\n")
        (self.repo / "lnk").symlink_to("/etc/hostname")
        git = ["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "init"], check=True)
        os.chmod(self.repo / "b", 0o600)
        self.env = dict(os.environ, AGENT_SHARE_STATE=str(base / "state"))
        self.cortex = grp.getgrnam("cortex").gr_gid

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def share(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(SHARE), str(self.repo), *args], env=self.env, text=True, capture_output=True, check=False)

    def test_share_check_restore(self) -> None:
        before = snapshot(self.repo)
        self.assertEqual(self.share().returncode, 0)
        self.assertEqual(self.share("--check").returncode, 1)
        self.assertEqual(snapshot(self.repo), before, "dry-run and --check change nothing")

        self.assertEqual(self.share("--apply").returncode, 0)
        self.assertEqual(self.share("--check").returncode, 0)
        b = (self.repo / "b").stat()
        self.assertEqual((b.st_gid, b.st_mode & 0o060), (self.cortex, 0o060))
        self.assertTrue((self.repo / "sub").stat().st_mode & 0o2000, "dirs get setgid")
        self.assertNotEqual((self.repo / "ign/x").stat().st_gid, self.cortex, "ignored paths untouched")

        restore = sorted(Path(self.env["AGENT_SHARE_STATE"]).glob("restore-*.sh"))
        self.assertEqual(len(restore), 1)
        subprocess.run(["bash", str(restore[0])], check=True, capture_output=True)
        self.assertEqual(snapshot(self.repo), before, "restore is exact")


if __name__ == "__main__":
    unittest.main()
