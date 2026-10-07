#!/usr/bin/env python3
"""End-to-end fixture for mailcortex-channel against the real mailcortex CLI."""

import json
import hashlib
import hmac
import os
import runpy
import subprocess
import tempfile
import time
import unittest
from email import policy
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

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


class ClubhouseIngressTest(unittest.TestCase):
    DESTINATION = "seat+worker@test.helm"
    SOURCE = "seat+coordinator@test.helm"
    MESSAGE_ID = "<clubhouse-fixture@example.test>"
    HANDOFF = "LOGS/handoffs/fixture.md"
    BODY = "Read LOGS/handoffs/fixture.md"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temporary.name)
        self.env = dict(os.environ,
                        MAILCORTEX_ROOT=str(self.tmp / "Mail"),
                        MAILCORTEX_RUNTIME=str(self.tmp / "state"))
        (self.tmp / "Mail").mkdir()
        self.environment = patch.dict(os.environ, self.env)
        self.environment.start()
        self.mc(["provision", self.DESTINATION, self.SOURCE])

        self.helm = self.tmp / "HelmCortex"
        handoff = self.helm / self.HANDOFF
        handoff.parent.mkdir(parents=True)
        handoff.write_text("fixture handoff v1\n")
        self.git("init", "-b", "master")
        self.git("add", self.HANDOFF)
        self.git("-c", "user.name=Fixture", "-c",
                 "user.email=fixture@example.test", "commit", "-m", "fixture v1")

        module = runpy.run_path(CHANNEL)
        self.ChannelError = module["ChannelError"]
        self.attempts = []
        self.projected = []
        self.fail_projection_once = False
        self.server = module["Server"](
            self.DESTINATION, [self.SOURCE], 0.2,
            clubhouse_root=self.helm,
            clubhouse_projector=self.projector,
        )
        self.notes = []
        self.logs = []
        self.server.write = self.notes.append
        self.server.log = self.logs.append

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def mc(self, args):
        return subprocess.run(["mailcortex", *args], env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.helm, check=True,
                              capture_output=True, text=True).stdout.strip()

    def projector(self, receipt, prompt, root):
        self.attempts.append((receipt, prompt, root))
        if self.fail_projection_once:
            self.fail_projection_once = False
            raise self.ChannelError("fixture projection failure")
        self.projected.append((receipt, prompt, root))

    def deliver(self, *, body=None, message_id=None, key="fixture-mail"):
        message = EmailMessage(policy=policy.SMTP)
        message["From"] = self.SOURCE
        message["To"] = self.DESTINATION
        message["Subject"] = "[BRIEF] fixture"
        message["Message-ID"] = message_id or self.MESSAGE_ID
        message.set_content(body if body is not None else self.BODY)
        target = Path(self.env["MAILCORTEX_ROOT"]) / "seats/worker/new" / key
        target.write_bytes(message.as_bytes())
        return target

    def receipt(self):
        paths = list((Path(self.env["MAILCORTEX_RUNTIME"]) /
                      "clubhouse-ingress/worker").glob("*.json"))
        self.assertEqual(len(paths), 1)
        return json.loads(paths[0].read_text())

    def current_message(self):
        maildir = Path(self.env["MAILCORTEX_ROOT"]) / "seats/worker"
        paths = [*maildir.joinpath("new").iterdir(), *maildir.joinpath("cur").iterdir()]
        self.assertEqual(len(paths), 1)
        return paths[0]

    def test_committed_brief_is_projected_once_and_equal_redelivery_is_idempotent(self):
        self.deliver()
        self.assertEqual(self.server.scan_once(), 1)
        self.assertEqual(len(self.projected), 1)
        self.assertEqual(len(self.notes), 1)
        receipt = self.receipt()
        self.assertEqual(receipt["principal_class"], "agent")
        self.assertEqual(receipt["recovery_state"], "dispatch_unknown")
        self.assertEqual(receipt["source_record_ref"]["handoff_path"], self.HANDOFF)
        self.assertEqual(receipt["source_record_ref"]["handoff_revision"],
                         self.git("rev-list", "-1", "master", "--", self.HANDOFF))
        self.assertEqual(self.server.scan_once(), 0)
        self.assertEqual(len(self.projected), 1)
        self.assertEqual(len(self.notes), 1)

    def test_changed_body_under_the_same_message_id_conflicts(self):
        self.deliver()
        self.server.scan_once()
        current = self.current_message()
        current.unlink()
        replacement = self.deliver(body="Changed private body", key=current.name)
        if current.parent.name == "cur":
            replacement.rename(current)
        with self.assertRaisesRegex(self.ChannelError, "conflict"):
            self.server.scan_once()
        self.assertEqual(len(self.projected), 1)

    def test_changed_handoff_revision_under_the_same_message_id_conflicts(self):
        self.deliver()
        self.server.scan_once()
        (self.helm / self.HANDOFF).write_text("fixture handoff v2\n")
        self.git("add", self.HANDOFF)
        self.git("-c", "user.name=Fixture", "-c",
                 "user.email=fixture@example.test", "commit", "-m", "fixture v2")
        with self.assertRaisesRegex(self.ChannelError, "conflict"):
            self.server.scan_once()
        self.assertEqual(len(self.projected), 1)

    def test_projection_failure_recovers_from_cur_without_double_notification(self):
        original = self.deliver()
        self.fail_projection_once = True
        with self.assertRaisesRegex(self.ChannelError, "projection"):
            self.server.scan_once()
        receipt = self.receipt()
        self.assertEqual(receipt["recovery_state"], "accepted_unprojected")
        seen = original.parent.parent / "cur" / (original.name + ":2,S")
        original.rename(seen)
        self.assertEqual(self.server.scan_once(), 1)
        self.assertEqual(len(self.attempts), 2)
        self.assertEqual(len(self.projected), 1)
        self.assertEqual(len(self.notes), 1)

    def test_handling_receipt_alone_cannot_project_a_swing(self):
        self.server.call("receipt", {
            "message_id": "<handling-only@example.test>",
            "state": "handling_completed",
        })
        self.assertEqual(self.attempts, [])
        self.assertFalse((Path(self.env["MAILCORTEX_RUNTIME"]) /
                          "clubhouse-ingress").exists())


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
