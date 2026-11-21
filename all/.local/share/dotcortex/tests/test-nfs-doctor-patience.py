#!/usr/bin/env python3
"""nfs-doctor must not call a busy NFS server stale, and must wait several runs before it unmounts anything."""
import os
import pathlib
import re
import stat
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[5]
DOCTOR = REPO / "all/.local/bin/nfs-doctor"


class PatienceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        self.stubs = self.root / "stubs"
        self.stubs.mkdir()
        self.state = self.root / "state"
        text = DOCTOR.read_text()
        match = re.search(r"STALE_STAT_TIMEOUT=.*?\nmount_is_stale\(\) \{.*?\n\}\n", text, re.S)
        self.assertIsNotNone(match, "the patient probe is missing from nfs-doctor")
        self.code = match.group(0)
        self.stub("timeout", 'shift; exec "$@"')
        self.stub("stat", 'exit "${STAT_RC:-0}"')
        self.stub("rpcinfo", 'exit "${RPC_RC:-0}"')

    def stub(self, name, body):
        path = self.stubs / name
        path.write_text("#!/bin/bash\n" + body + "\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def run_probe(self, stat_rc, rpc_rc, mp="/"):
        env = {"PATH": f"{self.stubs}:/usr/bin:/bin", "STAT_RC": str(stat_rc), "RPC_RC": str(rpc_rc),
               "NFS_DOCTOR_STATE": str(self.state)}
        script = 'log() { echo "log: $*"; }\n' + self.code + f'\nmount_is_stale "{mp}"; echo rc=$?'
        return subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=30).stdout

    def test_a_working_stat_is_never_stale(self):
        self.assertIn("rc=1", self.run_probe(0, 1))

    def test_a_slow_stat_while_the_server_answers_is_not_stale(self):
        out = self.run_probe(1, 0)
        self.assertIn("rc=1", out)
        self.assertIn("answers NFS", out)

    def test_a_dead_server_is_stale_only_after_the_third_consecutive_run(self):
        self.assertIn("rc=1", self.run_probe(1, 1))
        self.assertIn("rc=1", self.run_probe(1, 1))
        self.assertIn("rc=0", self.run_probe(1, 1))

    def test_one_good_run_resets_the_count(self):
        self.run_probe(1, 1)
        self.run_probe(1, 1)
        self.run_probe(0, 0)
        self.assertIn("rc=1", self.run_probe(1, 1))


if __name__ == "__main__":
    unittest.main()
