#!/usr/bin/env python3
from __future__ import annotations

import grp
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
SEAL = ROOT / "all/.local/bin/agent-home-seal"


def mode(p: Path) -> int:
    return stat.S_IMODE(p.lstat().st_mode)


@unittest.skipUnless(any(g.gr_name == "cortex" for g in grp.getgrall()), "needs the cortex group")
class AgentHomeSealTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.outside = base / "outside"
        self.home.mkdir(mode=0o700)
        self.outside.mkdir()
        self.outside.chmod(0o755)  # explicit: mkdir modes are masked by umask
        for name, m in ((".config", 0o775), ("DotCortex", 0o775), ("notes.log", 0o664)):
            p = self.home / name
            p.mkdir() if name != "notes.log" else p.write_text("x")
            p.chmod(m)
        env = self.home / ".env"
        env.write_text("A=1\n")
        env.chmod(0o664)
        (self.home / "link").symlink_to(self.outside)
        self.env = dict(
            os.environ,
            AGENT_SEAL_HOME=str(self.home),
            AGENT_SEAL_STATE=str(base / "state"),
            AGENT_SEAL_REACH="DotCortex",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def seal(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(SEAL), *args], env=self.env, text=True, capture_output=True, check=False)

    def test_dry_run_apply_restore(self) -> None:
        before = {p.name: mode(p) for p in self.home.iterdir()}
        dry = self.seal()
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual({p.name: mode(p) for p in self.home.iterdir()}, before, "dry-run must not change modes")

        done = self.seal("--apply")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(mode(self.home / ".config") & 0o007, 0)
        self.assertEqual(mode(self.home / "notes.log") & 0o007, 0)
        self.assertEqual(mode(self.home / ".env"), 0o600)
        self.assertEqual(mode(self.home / "DotCortex"), 0o775, "reach entries keep their mode")
        self.assertEqual(mode(self.outside), 0o755, "symlink targets are never touched")
        acl = subprocess.run(["getfacl", "-cp", str(self.home)], text=True, capture_output=True).stdout
        self.assertIn("group:cortex:--x", acl)

        restore = sorted((Path(self.env["AGENT_SEAL_STATE"])).glob("restore-*.sh"))
        self.assertEqual(len(restore), 1)
        subprocess.run(["bash", str(restore[0])], check=True, capture_output=True)
        self.assertEqual({p.name: mode(p) for p in self.home.iterdir()}, before, "restore puts every mode back")

    def test_missing_reach_entry_is_fatal(self) -> None:
        self.env["AGENT_SEAL_REACH"] = "NoSuchRepo"
        self.assertEqual(self.seal().returncode, 1)


if __name__ == "__main__":
    unittest.main()
