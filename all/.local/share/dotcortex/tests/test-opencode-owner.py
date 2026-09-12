from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import unittest


HERE = Path(__file__).resolve()
OWNER = HERE.parents[3] / "bin" / "opencode-owner"
PROJECT = "/home/metsatron/HelmCortex"


class OpenCodeOwnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name) / "opencode.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_state(self, **overrides: object) -> None:
        value = {
            "schema": "helmcortex.opencode-owner.v2",
            "owner": "telegram-agent-host:opencode",
            "bot": "opencode",
            "project": PROJECT,
            "host": "127.0.0.1",
            "port": 4096,
            "backend_pid": 999999991,
            "poller_pid": 999999992,
        }
        value.update(overrides)
        self.state.write_text(json.dumps(value), encoding="utf-8")

    def stop(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(OWNER), "stop", "--state", str(self.state), "--project", PROJECT,
             "--host", "127.0.0.1", "--port", "4096"],
            text=True, capture_output=True, timeout=10,
        )

    def test_exact_dead_preboot_owner_state_is_retired(self) -> None:
        self.write_state()
        result = self.stop()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("stale=2", result.stdout)
        self.assertFalse(self.state.exists())

    def test_foreign_dead_state_is_preserved(self) -> None:
        self.write_state(owner="someone-else")
        result = self.stop()
        self.assertEqual(result.returncode, 1)
        self.assertIn("foreign-owner", result.stderr)
        self.assertTrue(self.state.exists())

    def test_valid_survivor_is_stopped_while_dead_peer_is_retired(self) -> None:
        poller = Path(self.temp.name) / "poller"
        poller.write_text("#!/bin/sh\ntrap 'exit 0' TERM INT\nwhile :; do sleep 1; done\n", encoding="utf-8")
        poller.chmod(poller.stat().st_mode | stat.S_IXUSR)
        process = subprocess.Popen([str(poller), "start", "--mode", "installed"], cwd=PROJECT)
        try:
            time.sleep(0.1)
            proc = Path("/proc") / str(process.pid)
            raw_stat = (proc / "stat").read_text(encoding="utf-8")
            start_ticks = int(raw_stat[raw_stat.rfind(")") + 2 :].split()[19])
            argv = [part.decode() for part in (proc / "cmdline").read_bytes().split(b"\0") if part]
            self.write_state(
                poller_pid=process.pid,
                poller_start_ticks=start_ticks,
                poller_cwd=os.path.realpath(PROJECT),
                poller_argv=argv,
                poller_entrypoint=str(poller),
            )
            result = self.stop()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("stopped_owned=1 stale=1 refused=0", result.stdout)
            self.assertFalse(self.state.exists())
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
