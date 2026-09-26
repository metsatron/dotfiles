#!/usr/bin/env python3
"""agent-cli-install host lanes (agents-bots-honey.org, "Flying Fox and Possum lanes"). Dry-run only, no root."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
INSTALL = ROOT / "all/.local/bin/agent-cli-install"
MANIFESTS = ROOT / "all/.config/agent-cli"


class AgentCliLaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        stub = Path(self.tmp.name) / "bin"
        stub.mkdir()
        (stub / "id").write_text("#!/bin/sh\nexit 0\n")  # every agent user "exists"
        (stub / "id").chmod(0o755)
        self.env = dict(os.environ, PATH=f"{stub}:{os.environ['PATH']}", AGENT_CLI_MANIFESTS=str(MANIFESTS))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def dry(self, host: str, only: str) -> str:
        out = subprocess.run(["bash", str(INSTALL), "--only", only], env=dict(self.env, AGENT_CLI_HOST=host),
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn("+ ", out.stdout, "dry-run must not run anything")
        return out.stdout

    def test_honey_codex_uses_its_host_lane(self) -> None:
        out = self.dry("beelink", "codex")
        self.assertIn("hosts/beelink@agent-codex.ssv", out)
        self.assertIn("@openai/codex@0.154.0", out)
        self.assertNotIn("@openai/codex@0.133.0", out)

    def test_honey_opencode_uses_its_host_lane(self) -> None:
        out = self.dry("beelink", "opencode")
        self.assertIn("opencode-ai@1.18.30", out)
        self.assertIn("@grinev/opencode-telegram-bot@0.25.2", out)
        self.assertNotIn("agent-browser", out)

    def test_other_hosts_keep_the_fleet_pins(self) -> None:
        out = self.dry("kikin-kushi", "codex,opencode")
        self.assertNotIn("host lane", out)
        self.assertIn("@openai/codex@0.133.0", out)
        self.assertIn("agent-browser@", out)

    def test_host_lanes_only_name_provisioned_agents(self) -> None:
        tools = {l.split()[0] for l in (MANIFESTS / "uids.ssv").read_text().splitlines()
                 if l.strip() and not l.startswith("#") and l.split()[2] == "yes"}
        for lane in (MANIFESTS / "hosts").glob("*@agent-*.ssv"):
            self.assertIn(lane.stem.split("@agent-", 1)[1], tools, lane.name)


if __name__ == "__main__":
    unittest.main()
