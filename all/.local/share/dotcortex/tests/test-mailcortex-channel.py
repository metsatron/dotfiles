#!/usr/bin/env python3
"""End-to-end fixture for mailcortex-channel against the real mailcortex CLI."""

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

CHANNEL = os.environ.get("MAILCORTEX_CHANNEL", str(Path("~/.local/bin/mailcortex-channel").expanduser()))
AGENT, FACE, STRANGER = "fable@test.helm", "seat+xmpp-bridge@test.helm", "stranger@test.helm"


class ChannelTest(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.env = dict(os.environ, MAILCORTEX_ROOT=str(tmp / "Mail"), MAILCORTEX_RUNTIME=str(tmp / "state"))
        (tmp / "Mail").mkdir()
        self.mc(["provision", AGENT, FACE, STRANGER])
        self.proc = subprocess.Popen(
            [CHANNEL, "--address", AGENT, "--allow-from", FACE, "--poll", "0.2"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=self.env)
        self.tmp = tmp

    def tearDown(self):
        self.proc.kill()
        self.proc.wait()

    def mc(self, args):
        return subprocess.run(["mailcortex", *args], env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def send(self, payload):
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def recv(self):
        return json.loads(self.proc.stdout.readline())

    def test_round_trip(self):
        self.send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        init = self.recv()
        self.assertIn("claude/channel", init["result"]["capabilities"]["experimental"])
        self.assertNotIn("claude/channel/permission", init["result"]["capabilities"]["experimental"])
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = {t["name"] for t in self.recv()["result"]["tools"]}
        self.assertEqual(tools, {"reply", "receipt"})

        self.mc(["send", "--from", STRANGER, "--to", AGENT, "--subject", "nope", "--body", "ignore me"])
        self.mc(["send", "--from", FACE, "--to", AGENT, "--subject", "[xmpp] hi", "--body", "hello agent"])
        note = self.recv()
        self.assertEqual(note["method"], "notifications/claude/channel")
        self.assertEqual(note["params"]["content"], "hello agent")
        self.assertEqual(note["params"]["meta"]["from"], FACE)
        mid = note["params"]["meta"]["message_id"]

        states = [line.split("\t")[0] + ":" + line.split("\t")[3] for line in self.mc(["inbox", AGENT]).splitlines()]
        self.assertIn("new:" + STRANGER, states)
        self.assertIn("cur:" + FACE, states)

        self.send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                   "params": {"name": "reply", "arguments": {"to": FACE, "text": "hello human", "in_reply_to": mid}}})
        result = self.recv()["result"]
        self.assertFalse(result["isError"], result)
        rows = self.mc(["inbox", FACE]).splitlines()
        self.assertEqual(len(rows), 1)
        self.assertIn(AGENT, rows[0])
        receipts = list((self.tmp / "state" / "receipts" / "fable").glob("*.json"))
        self.assertEqual(len(receipts), 1)
        self.assertIn("handling_completed", receipts[0].read_text())

        self.send({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                   "params": {"name": "reply", "arguments": {"to": "not an address", "text": "x"}}})
        self.assertTrue(self.recv()["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
