#!/usr/bin/env python3
"""End-to-end fixture for mailcortex-channel against the real mailcortex CLI."""

import json
import hashlib
import hmac
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
        reply_name = rows[0].split("\t")[1]
        reply_rendered = self.mc(["read", FACE, reply_name])
        self.assertIn("In-Reply-To: " + mid, reply_rendered)
        self.assertIn("References: " + mid, reply_rendered)
        receipts = list((self.tmp / "state" / "receipts" / "fable").glob("*.json"))
        self.assertEqual(len(receipts), 1)
        self.assertIn("handling_completed", receipts[0].read_text())

        self.send({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                   "params": {"name": "reply", "arguments": {"to": "not an address", "text": "x"}}})
        self.assertTrue(self.recv()["result"]["isError"])


class PermissionChannelTest(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.tmp = tmp
        self.env = dict(os.environ, MAILCORTEX_ROOT=str(tmp / "Mail"), MAILCORTEX_RUNTIME=str(tmp / "state"))
        (tmp / "Mail").mkdir()
        self.mc(["provision", AGENT, FACE, STRANGER])
        self.secret = tmp / "permission.secret"
        self.secret.write_text("s" * 32)
        self.secret.chmod(0o600)
        self.proc = subprocess.Popen(
            [CHANNEL, "--address", AGENT, "--allow-from", FACE,
             "--permission-secret", str(self.secret), "--bridge-address", FACE,
             "--poll", "0.2"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=self.env)
        self.send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-06-18"}})
        init = self.recv()
        self.assertIn("claude/channel/permission", init["result"]["capabilities"]["experimental"])
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

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

    def auth(self, seat, request_id, behavior, timestamp):
        stamp = str(timestamp)
        material = f"{seat} | {request_id} | {behavior} | {stamp}".encode()
        digest = hmac.new(b"s" * 32, material, hashlib.sha256).hexdigest()
        return (f"seat={seat};request_id={request_id};behavior={behavior};"
                f"timestamp={stamp};hmac={digest}")

    def deliver(self, body="Permission decision", auth=None):
        args = ["send", "--from", FACE, "--to", AGENT,
                "--subject", "permission", "--body", body]
        if auth is not None:
            args.extend(["--permission-auth", auth])
        self.mc(args)

    def ordinary(self):
        note = self.recv()
        self.assertEqual(note["method"], "notifications/claude/channel")
        return note

    def test_permission_request_shape_and_forged_decisions(self):
        self.send({"jsonrpc": "2.0", "method": "notifications/claude/channel/permission_request",
                   "params": {"request_id": "abcde", "tool_name": "Bash",
                               "description": "run a command", "input_preview": "echo fixture"}})
        for _ in range(50):
            rows = self.mc(["inbox", FACE]).splitlines()
            if rows:
                break
            time.sleep(0.02)
        self.assertEqual(len(rows), 1)
        request = self.mc(["read", FACE, rows[0].split("\t")[1]])
        self.assertIn("Subject: [permission] Bash", request)
        self.assertIn("request_id: abcde", request)
        self.assertIn("yes abcde / no abcde", request)

        self.deliver(auth=None)
        self.ordinary()
        self.deliver(auth=self.auth("fable", "abcde", "allow", int(time.time() - 601)))
        self.ordinary()
        valid_auth = self.auth("fable", "abcde", "allow", int(time.time()))
        forged = valid_auth[:-1] + ("0" if valid_auth[-1] != "0" else "1")
        self.deliver(auth=forged)
        self.ordinary()
        self.deliver(auth=self.auth("fable", "bcdef", "allow", int(time.time())))
        self.ordinary()
        self.deliver(auth=self.auth("worker", "abcde", "allow", int(time.time())))
        self.ordinary()

        self.deliver(body="yes abcde", auth=self.auth("fable", "abcde", "allow", int(time.time())))
        decision = self.recv()
        self.assertEqual(decision["method"], "notifications/claude/channel/permission")
        self.assertEqual(decision["params"], {"request_id": "abcde", "behavior": "allow"})
        self.deliver(body="yes abcde", auth=self.auth("fable", "abcde", "allow", int(time.time())))
        self.ordinary()


if __name__ == "__main__":
    unittest.main()
