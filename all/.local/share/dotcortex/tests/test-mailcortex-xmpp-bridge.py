#!/usr/bin/env python3
"""Fixture tests for mailcortex-xmpp-bridge (no network, no slixmpp)."""

import asyncio
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import threading
import types
import unittest
import xml.etree.ElementTree as ET
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import patch

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


class VoiceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp = Path(temporary.name)
        data = base_config(self.tmp) | {"upload_base_url": "https://uploads.example.test/file_share/"}
        config = self.tmp / "bridge.json"
        config.write_text(json.dumps(data))
        self.cfg = bridge.load_config(config)
        self.url = self.cfg["upload_base_url"] + "slot/note.ogg"
        self.audio_paths = []
        self.raw = b"OggS\x00original voice"

    def download(self, cfg, url, path):
        self.audio_paths.append(path)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        path.write_bytes(self.raw)
        path.chmod(0o600)

    def test_oob_and_url_only_detection(self):
        for body in ("", "caption", self.url):
            self.assertEqual(bridge.voice_url(self.cfg, FakeMessage(body, self.url)), self.url)
        self.assertEqual(bridge.voice_url(self.cfg, FakeMessage(self.url)), self.url)
        self.assertIsNone(bridge.voice_url(self.cfg, FakeMessage("See " + self.url)))
        self.assertIsNone(bridge.voice_url(self.cfg, FakeMessage("hello")))

    def test_plain_foreign_http_and_unconfigured_links_arrive_as_text_mail(self):
        root = self.tmp / "Mail"
        maildir = root / "consorts/fable"
        for leaf in ("tmp", "new", "cur"):
            (maildir / leaf).mkdir(parents=True)
        command = Path(__file__).resolve().parents[5] / "all/.local/bin/mailcortex"
        original = bridge.inbound_mail
        def run(argv, **kwargs):
            self.assertNotIn("--attach", argv)
            return subprocess.run([str(command), *argv[1:]],
                                  env=os.environ | {"MAILCORTEX_ROOT": str(root)}, **kwargs)
        def text_mail(cfg, sender, local, body):
            return original(cfg, sender, local, body, run)
        cases = ((self.cfg, "https://foreign.example.test/article"),
                 (self.cfg, self.url.replace("https:", "http:")),
                 (self.cfg | {"upload_base_url": ""}, self.url))
        for cfg, link in cases:
            with self.subTest(link=link, configured=bool(cfg["upload_base_url"])):
                msg = FakeMessage(link)
                before = set((maildir / "new").iterdir())
                with patch.object(bridge, "inbound_mail", side_effect=text_mail), \
                        patch.object(bridge, "inbound_voice", side_effect=AssertionError("plain link entered voice lane")):
                    asyncio.run(bridge.deliver_inbound(cfg, msg, "owner@example.test", "fable",
                                                      bridge.voice_url(cfg, msg)))
                delivered, = set((maildir / "new").iterdir()) - before
                message = BytesParser(policy=policy.default).parsebytes(delivered.read_bytes())
                self.assertFalse(message.is_multipart())
                self.assertTrue(str(message["Subject"]).startswith("[xmpp] "))
                self.assertEqual(message["To"], "fable@host.helm")
                body = message.get_content().replace("\r\n", "\n")
                self.assertIn("\n\n" + link + "\n", body)
                self.assertEqual(msg.replies, [])

    def test_oob_foreign_http_and_unconfigured_links_keep_refusal(self):
        cases = ((self.cfg, "https://foreign.example.test/file_share/slot/note.ogg"),
                 (self.cfg, self.url.replace("https:", "http:")),
                 (self.cfg | {"upload_base_url": ""}, self.url))
        for cfg, link in cases:
            msg = FakeMessage(self.url, link)
            with patch.object(bridge, "download_voice") as download, \
                    patch.object(bridge, "transcribe_voice", return_value="fixture words") as transcribe, \
                    patch.object(bridge, "mailcortex", return_value="fixture.msg") as mail:
                self.assertEqual(bridge.voice_url(cfg, msg), link)
                with self.assertLogs(bridge.LOG, level="ERROR"):
                    asyncio.run(bridge.deliver_inbound(cfg, msg, "owner@example.test", "fable",
                                                      bridge.voice_url(cfg, msg)))
                download.assert_not_called()
                transcribe.assert_not_called()
                mail.assert_not_called()
            self.assertEqual(len(msg.replies), 1)
            self.assertTrue(msg.replies[0].startswith("Voice note could not be transcribed: "))

    def test_foreign_host_refused_before_fetch_transcribe_or_mail(self):
        run = FakeRun()
        for url in ("https://evil.example.test/file_share/slot/note.ogg",
                    "https://uploads.example.test.evil.test/file_share/slot/note.ogg"):
            with self.assertRaisesRegex(bridge.BridgeError, "foreign upload host"):
                bridge.inbound_voice(self.cfg, "owner@example.test", "fable", url,
                                     run, self.download, lambda _: "hello")
        self.assertEqual(self.audio_paths, [])
        self.assertEqual(run.calls, [])

    def test_https_port_path_and_config_guards(self):
        for url in (self.url.replace("https:", "http:"),
                    self.url.replace("uploads.example.test", "uploads.example.test:444"),
                    self.url.replace("/file_share/", "/private/"),
                    self.url.replace("slot/", "../"),
                    self.url.replace("slot/", "%2e%2e/"),
                    self.url + "?token=fixture", self.url + "#fragment",
                    self.url.replace("https://", "https://user:password@")):
            with self.assertRaises(bridge.BridgeError):
                bridge.validate_upload_url(self.cfg, url)
        with self.assertRaisesRegex(bridge.BridgeError, "not configured"):
            bridge.validate_upload_url(self.cfg | {"upload_base_url": ""}, self.url)
        for base in ("http://uploads.example.test/file_share/", "https://uploads.example.test/",
                     "https://uploads.example.test/file_share", 42):
            path = self.tmp / "invalid.json"
            path.write_text(json.dumps(base_config(self.tmp) | {"upload_base_url": base}))
            with self.assertRaises(bridge.BridgeError):
                bridge.load_config(path)

    def test_download_stream_size_headers_permissions_and_failures(self):
        class Response(io.BytesIO):
            status = 200
            def __init__(self, payload, length=None):
                super().__init__(payload)
                self.headers = {} if length is None else {"Content-Length": str(length)}
        def opener(response):
            def open_(request, timeout):
                self.assertEqual(request.full_url, self.url)
                self.assertEqual(timeout, 5)
                return response
            return open_
        good = self.tmp / "good.ogg"
        bridge.download_voice(self.cfg, self.url, good, opener(Response(self.raw, len(self.raw))))
        self.assertEqual(good.read_bytes(), self.raw)
        self.assertEqual(good.stat().st_mode & 0o777, 0o600)
        for response in (Response(b"", bridge.VOICE_LIMIT + 1), Response(b""),
                         Response(b"a", 10), Response(b"a", "not-a-number")):
            with self.assertRaises(bridge.BridgeError):
                bridge.download_voice(self.cfg, self.url, self.tmp / "bad", opener(response))
            if (self.tmp / "bad").exists():
                (self.tmp / "bad").unlink()
        with patch.object(bridge, "VOICE_LIMIT", 4):
            with self.assertRaisesRegex(bridge.BridgeError, "exceeds"):
                bridge.download_voice(self.cfg, self.url, self.tmp / "stream-cap", opener(Response(b"abcde")))
        with patch.object(bridge.time, "monotonic", side_effect=[0, 31]):
            with self.assertRaisesRegex(bridge.BridgeError, "timed out"):
                bridge.download_voice(self.cfg, self.url, self.tmp / "timeout", opener(Response(b"a")))
        with self.assertRaisesRegex(bridge.BridgeError, "redirects refused"):
            bridge.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.example.test/")
        with patch.object(bridge.urllib.request, "build_opener") as build:
            build.return_value.open.side_effect = OSError("TLS failed")
            with self.assertRaisesRegex(bridge.BridgeError, "download failed"):
                bridge.download_voice(self.cfg, self.url, self.tmp / "tls-failure")
            self.assertEqual(build.call_args.args[0].proxies, {})
            self.assertIsInstance(build.call_args.args[1], bridge.NoRedirect)

    def test_transcriber_cli_quality_and_empty_refusals(self):
        audio = self.tmp / "voice.ogg"
        audio.write_bytes(self.raw)
        def runner(raw, status=0):
            def run(argv, **kwargs):
                self.assertEqual(argv[:2], [str(Path.home() / "HelmCortex/FORGE/bin/whisper-transcribe"), str(audio)])
                self.assertEqual(kwargs["timeout"], 600)
                Path(argv[argv.index("--out") + 1]).write_text(raw)
                return subprocess.CompletedProcess(argv, status, "", "")
            return run
        self.assertEqual(bridge.transcribe_voice(audio, runner("---\nwhisper_quality: clean\n---\n\nSpoken words.\n")), "Spoken words.")
        for raw, status in (("---\nwhisper_quality: clean\n---\n\n", 0),
                            ("---\nwhisper_quality: suspect\n---\nwords", 4),
                            ("---\nwhisper_quality: non-speech\n---\n[non-speech audio]", 0),
                            ("words without provenance", 0)):
            with self.assertRaises(bridge.BridgeError):
                bridge.transcribe_voice(audio, runner(raw, status))
        for error in (subprocess.TimeoutExpired("whisper", 600), FileNotFoundError("whisper")):
            with patch.object(bridge.subprocess, "run", side_effect=error) as run:
                with self.assertRaises(bridge.BridgeError):
                    bridge.transcribe_voice(audio, run)

    def test_voice_mail_real_mime_roundtrip_and_temp_cleanup(self):
        root = self.tmp / "Mail"
        maildir = root / "consorts/fable"
        for leaf in ("tmp", "new", "cur"):
            (maildir / leaf).mkdir(parents=True)
        command = Path(__file__).resolve().parents[5] / "all/.local/bin/mailcortex"
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            self.assertEqual(Path(argv[argv.index("--attach") + 1]).read_bytes(), self.raw)
            return subprocess.run([str(command), *argv[1:]], env=os.environ | {"MAILCORTEX_ROOT": str(root)}, **kwargs)
        name = bridge.inbound_voice(self.cfg, "owner@example.test/phone", "fable",
                                    self.url, run, self.download, lambda _: "Spoken words.")
        self.assertEqual(len(calls), 1)
        message = BytesParser(policy=policy.default).parsebytes((maildir / "new" / name).read_bytes())
        self.assertEqual(message["Subject"], "[xmpp voice] Spoken words.")
        self.assertEqual(message["To"], "fable@host.helm")
        self.assertEqual(message["From"], self.cfg["bridge_address"])
        body = message.get_body(preferencelist=("plain",)).get_content().replace("\r\n", "\n")
        self.assertIn("\n\nSpoken words.\n", body)
        self.assertIn("XMPP-From: owner@example.test", message.get_body().get_content())
        part, = message.iter_attachments()
        self.assertEqual(part.get_filename(), "voice-note.ogg")
        self.assertEqual(part.get_payload(decode=True), self.raw)
        self.assertFalse(self.audio_paths[0].parent.exists())
        self.assertEqual(list((maildir / "tmp").iterdir()), [])

    def test_empty_and_failed_transcription_cleanup_without_mail(self):
        run = FakeRun()
        for transcriber in (lambda _: "", lambda _: (_ for _ in ()).throw(bridge.BridgeError("whisper failed"))):
            with self.assertRaises(bridge.BridgeError):
                bridge.inbound_voice(self.cfg, "owner@example.test", "fable", self.url,
                                     run, self.download, transcriber)
            self.assertFalse(self.audio_paths[-1].parent.exists())
        self.assertEqual(run.calls, [])
        def failed_download(cfg, url, path):
            self.download(cfg, url, path)
            raise bridge.BridgeError("fetch failed after partial write")
        with self.assertRaises(bridge.BridgeError):
            bridge.inbound_voice(self.cfg, "owner@example.test", "fable", self.url,
                                 run, failed_download, lambda _: "should not run")
        self.assertFalse(self.audio_paths[-1].parent.exists())
        self.assertEqual(run.calls, [])

    def test_failure_replies_once_and_worker_leaves_loop_responsive(self):
        msg = FakeMessage(self.url)
        async def failure():
            with patch.object(bridge, "inbound_voice", side_effect=bridge.BridgeError("whisper failed\nretry")):
                with self.assertLogs(bridge.LOG, level="ERROR"):
                    await bridge.deliver_inbound(self.cfg, msg, "owner@example.test", "fable", self.url)
        asyncio.run(failure())
        self.assertEqual(msg.replies, ["Voice note could not be transcribed: whisper failed retry"])
        started, release = threading.Event(), threading.Event()
        def slow(*args):
            started.set()
            if not release.wait(2):
                raise bridge.BridgeError("test worker was not released")
            return "delivered.msg"
        async def responsive():
            with patch.object(bridge, "inbound_voice", side_effect=slow):
                job = asyncio.create_task(bridge.deliver_inbound(self.cfg, FakeMessage(self.url),
                                          "owner@example.test", "fable", self.url))
                try:
                    for _ in range(100):
                        if started.is_set():
                            break
                        await asyncio.sleep(0.005)
                    self.assertTrue(started.is_set())
                    self.assertFalse(job.done())
                finally:
                    release.set()
                    await job
        asyncio.run(responsive())


class FakeMessage:
    def __init__(self, body, oob=None, sender="owner@example.test/phone", local="fable", mid="fixture-id"):
        self.xml = ET.Element("message")
        if oob:
            ET.SubElement(ET.SubElement(self.xml, "{jabber:x:oob}x"), "{jabber:x:oob}url").text = oob
        self.values = {"body": body, "type": "chat", "from": sender,
                       "to": types.SimpleNamespace(user=local), "id": mid}
        self.replies = []
    def __getitem__(self, key):
        return self.values[key]
    def reply(self, text):
        self.replies.append(text)
        return self
    def send(self):
        pass


class ComponentVoiceTests(unittest.TestCase):
    setUp = VoiceTests.setUp

    # Exercise the registered production handler, not only helper calls.
    def test_production_handler_bodyless_owner_dedupe_unknown_and_capacity(self):
        loop = asyncio.new_event_loop()
        self.addCleanup(loop.close)
        asyncio.set_event_loop(loop)
        self.addCleanup(asyncio.set_event_loop, None)
        instances = []
        class ComponentBase:
            def __init__(self, *args):
                self.disconnected = loop.create_future()
                self.handlers = {}
                instances.append(self)
            def register_plugin(self, name):
                pass
            def add_event_handler(self, name, handler):
                self.handlers[name] = handler
            def connect(self):
                self.disconnected.set_result(None)
        with patch.dict("sys.modules", {"slixmpp": types.SimpleNamespace(ComponentXMPP=ComponentBase)}), \
                patch.object(bridge, "state_root", return_value=self.tmp / "state"):
            self.assertEqual(bridge.run_bridge(self.cfg), 1)
        component, = instances
        async def exercise():
            with patch.object(bridge, "inbound_voice", return_value="voice.msg") as worker:
                owner = FakeMessage("", self.url)
                await component.handlers["message"](owner)
                worker.assert_called_once_with(self.cfg, "owner@example.test", "fable", self.url)
                await component.handlers["message"](owner)
                self.assertEqual(worker.call_count, 1)
                await component.handlers["message"](FakeMessage("", self.url, sender="evil@example.test"))
                self.assertEqual(worker.call_count, 1)
                ghost = FakeMessage("", self.url, local="ghost")
                await component.handlers["message"](ghost)
                self.assertEqual(ghost.replies, ["No such seat."])
                component.voice_jobs = bridge.VOICE_JOBS
                full = FakeMessage("", self.url, mid="new-id")
                await component.handlers["message"](full)
                self.assertEqual(worker.call_count, 1)
                self.assertIn("capacity reached", full.replies[0])
                # Plain links stay deliverable even when voice workers are full.
                with patch.object(bridge, "inbound_mail", return_value="text.msg") as text:
                    for index, link in enumerate(("https://foreign.example.test/article",
                                                  self.url.replace("https:", "http:"))):
                        plain = FakeMessage(link, mid=f"plain-{index}")
                        await component.handlers["message"](plain)
                        text.assert_called_with(self.cfg, "owner@example.test", "fable", link)
                        self.assertEqual(plain.replies, [])
                    self.cfg["upload_base_url"] = ""
                    unconfigured = FakeMessage(self.url, mid="plain-unconfigured")
                    await component.handlers["message"](unconfigured)
                    text.assert_called_with(self.cfg, "owner@example.test", "fable", self.url)
                    self.assertEqual(unconfigured.replies, [])
                    self.assertEqual(text.call_count, 3)
                self.assertEqual(worker.call_count, 1)
        loop.run_until_complete(exercise())


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
