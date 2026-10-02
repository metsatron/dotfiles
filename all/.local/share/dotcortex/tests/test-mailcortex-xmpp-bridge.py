#!/usr/bin/env python3
"""Fixture tests for mailcortex-xmpp-bridge (no network, no slixmpp)."""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

BRIDGE = Path(os.environ.get("MAILCORTEX_XMPP_BRIDGE", "~/.local/bin/mailcortex-xmpp-bridge")).expanduser()
loader = importlib.machinery.SourceFileLoader("bridge", str(BRIDGE))
spec = importlib.util.spec_from_loader("bridge", loader)
bridge = importlib.util.module_from_spec(spec)
loader.exec_module(bridge)


def base_config(tmp: Path) -> dict:
    secret = tmp / "secret"
    secret.write_text("s" * 32)
    os.chmod(secret, 0o600)
    return {
        "component_jid": "seats.example.test",
        "owner_jids": ["owner@example.test"],
        "bridge_address": "seat+xmpp-bridge@host.helm",
        "component_secret_file": str(secret),
        "seats": {"fable": "fable@host.helm", "worker": "seat+worker@host.helm"},
    }


class FakeRun:
    def __init__(self, outputs=None):
        self.calls = []
        self.outputs = outputs or {}

    def __call__(self, argv, capture_output, text):
        self.calls.append(argv)
        out = self.outputs.get(argv[1], "")
        return subprocess.CompletedProcess(argv, 0, out, "")


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def write(self, data):
        path = self.tmp / "bridge.json"
        path.write_text(json.dumps(data))
        return path

    def test_valid_config_builds_reverse_map(self):
        cfg = bridge.load_config(self.write(base_config(self.tmp)))
        self.assertEqual(cfg["bridge_seat"], "xmpp-bridge")
        self.assertEqual(cfg["reverse"]["fable"], "fable")

    def test_bridge_address_must_be_a_seat(self):
        data = base_config(self.tmp)
        data["bridge_address"] = "bridge@host.helm"
        with self.assertRaises(bridge.BridgeError):
            bridge.load_config(self.write(data))

    def test_duplicate_target_refused(self):
        data = base_config(self.tmp)
        data["seats"]["other"] = "fable@host.helm"
        with self.assertRaises(bridge.BridgeError):
            bridge.load_config(self.write(data))

    def test_owner_must_be_bare_jid(self):
        data = base_config(self.tmp)
        data["owner_jids"] = ["owner@example.test/phone"]
        with self.assertRaises(bridge.BridgeError):
            bridge.load_config(self.write(data))

    def test_secret_mode_enforced(self):
        cfg = bridge.load_config(self.write(base_config(self.tmp)))
        os.chmod(cfg["component_secret_file"], 0o644)
        with self.assertRaises(bridge.BridgeError):
            bridge.read_secret(cfg["component_secret_file"])


class GateTests(unittest.TestCase):
    def test_stranger_refused(self):
        gate = bridge.Gate(["owner@example.test"], 3)
        self.assertEqual(gate.admit("evil@example.test/x", 0), "unauthorized")

    def test_resource_stripped_and_rate_limited(self):
        gate = bridge.Gate(["owner@example.test"], 2)
        self.assertIsNone(gate.admit("Owner@example.test/phone", 0))
        self.assertIsNone(gate.admit("owner@example.test/laptop", 1))
        self.assertEqual(gate.admit("owner@example.test", 2), "rate_limited")
        self.assertIsNone(gate.admit("owner@example.test", 61))


class SeenTests(unittest.TestCase):
    def test_dedupe_persists_across_instances(self):
        path = Path(tempfile.mkdtemp()) / "seen.json"
        self.assertTrue(bridge.Seen(path).check_and_add("k1"))
        again = bridge.Seen(path)
        self.assertFalse(again.check_and_add("k1"))
        self.assertTrue(again.check_and_add(None))


class RoutingTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "bridge.json"
        path.write_text(json.dumps(base_config(tmp)))
        self.cfg = bridge.load_config(path)

    def test_inbound_sends_from_bridge_to_seat(self):
        run = FakeRun({"send": "123.msg\n"})
        name = bridge.inbound_mail(self.cfg, "owner@example.test/phone", "fable", "Hello there\nsecond line", run)
        self.assertEqual(name, "123.msg")
        argv = run.calls[0]
        self.assertEqual(argv[:6], ["mailcortex", "send", "--from", "seat+xmpp-bridge@host.helm", "--to", "fable@host.helm"])
        self.assertEqual(argv[argv.index("--subject") + 1], "[xmpp] Hello there")
        body = argv[argv.index("--body") + 1]
        self.assertIn("XMPP-From: owner@example.test\n", body)
        self.assertIn("--to seat+xmpp-bridge@host.helm", body)

    def test_inbound_unknown_seat_sends_nothing(self):
        run = FakeRun()
        with self.assertRaises(bridge.BridgeError):
            bridge.inbound_mail(self.cfg, "owner@example.test", "ghost", "hi", run)
        self.assertEqual(run.calls, [])

    def test_pending_only_new(self):
        run = FakeRun({"inbox": "cur\told\td\tf\ts\nnew\tfresh\td\tf\ts\n"})
        self.assertEqual(bridge.pending_outbound(self.cfg, run), ["fresh"])

    def test_outbound_maps_sender_and_keeps_subject(self):
        rendered = ("Date: x\nFrom: fable@host.helm\nTo: seat+xmpp-bridge@host.helm\n"
                    "Subject: Build finished\nMessage-ID: <1@host.helm>\n\nAll green.\n")
        local, text, mid = bridge.render_outbound(self.cfg, rendered)
        self.assertEqual((local, mid), ("fable", "<1@host.helm>"))
        self.assertEqual(text, "Build finished\n\nAll green.")

    def test_outbound_reply_subject_dropped(self):
        rendered = ("From: seat+worker@host.helm\nSubject: Re: [xmpp] Hello\n"
                    "Message-ID: <2@host.helm>\n\nDone.\n")
        self.assertEqual(bridge.render_outbound(self.cfg, rendered)[:2], ("worker", "Done."))

    def test_outbound_sender_from_another_machine_maps(self):
        rendered = ("From: seat+worker@other-node.helm\nSubject: Re: [xmpp] Hey\n"
                    "Message-ID: <4@other-node.helm>\n\nOn it.\n")
        self.assertEqual(bridge.render_outbound(self.cfg, rendered)[:2], ("worker", "On it."))

    def test_outbound_unmapped_sender(self):
        rendered = "From: stranger@host.helm\nSubject: x\nMessage-ID: <3@host.helm>\n\nhi\n"
        self.assertIsNone(bridge.render_outbound(self.cfg, rendered)[0])


if __name__ == "__main__":
    unittest.main()
