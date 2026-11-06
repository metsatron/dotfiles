#!/usr/bin/env python3
"""Tests for Aura's MailCortex forced-command wrapper (services-mailcortex.org)."""
import importlib.machinery
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve()
WRAPPER = HERE.parents[5] / "all/.local/bin/mailcortex-aura-wrapper"

INBOX = ("seen\t111.1_a.kikin-kushi\tFri\thermes@kikin.helm\tOld\n"
         "new\t222.2_b.kikin-kushi\tSat\thermes@kikin.helm\tWake test ABC\n"
         "new\t333.3_c.kikin-kushi\tSat\tfable@kikin.helm\tHello\n")
MESSAGE = ("Date: Sat\nFrom: Hermes <hermes@kikin.helm>\nTo: aura@honey.helm\n"
           "Subject: Wake test ABC\nMessage-ID: <222.2.99@kikin.helm>\n\nbody\n")


class Fake:
    def __init__(self, send_rc=0):
        self.calls, self.send_rc = [], send_rc

    def __call__(self, argv, env=None, capture_output=False, text=False, **kw):
        args = argv[1:]
        self.calls.append(args)
        out = mock.Mock(returncode=0, stdout="", stderr="")
        if args[0] == "inbox":
            out.stdout = INBOX
        elif args[0] == "read":
            out.stdout = MESSAGE if args[2] == "222.2_b.kikin-kushi" else ""
            out.returncode = 0 if out.stdout else 1
        elif args[0] == "send":
            out.returncode = self.send_rc
        return out


def load(tmp):
    loader = importlib.machinery.SourceFileLoader("aura_wrapper_test", str(WRAPPER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    mod.LAST = os.path.join(tmp, "last.json")
    mod.LOG = os.path.join(tmp, "lane.log")
    return mod


def run(mod, fake, command, stdin=b""):
    env = {"SSH_ORIGINAL_COMMAND": command}
    buf = mock.Mock(buffer=io.BytesIO(stdin))
    with mock.patch.dict(os.environ, env), mock.patch.object(mod.subprocess, "run", fake), \
            mock.patch.object(sys, "stdin", buf), mock.patch("sys.stdout", new_callable=io.StringIO), \
            mock.patch("sys.stderr", new_callable=io.StringIO) as err:
        try:
            mod.main()
        except SystemExit as stop:
            return stop.code, err.getvalue()
    return 0, err.getvalue()


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aura-wrapper-test-")
        self.mod = load(self.tmp)

    def test_read_next_opens_oldest_unread_and_remembers_it(self):
        fake = Fake()
        code, _ = run(self.mod, fake, "read next")
        self.assertEqual(code, 0)
        self.assertIn(["read", "aura@honey.helm", "222.2_b.kikin-kushi"], fake.calls)
        meta = json.load(open(self.mod.LAST))
        self.assertEqual(meta["message-id"], "<222.2.99@kikin.helm>")
        self.assertFalse(meta["replied"])

    def test_mistyped_name_is_refused_with_the_short_form(self):
        code, err = run(self.mod, Fake(), "read 2222.2_b")
        self.assertEqual(code, 2)
        self.assertIn("read next", err)

    def test_reply_derives_recipient_thread_subject_and_receipt(self):
        fake = Fake()
        run(self.mod, fake, "read next")
        code, _ = run(self.mod, fake, "reply", b"received ABC\n")
        self.assertEqual(code, 0)
        send = [c for c in fake.calls if c[0] == "send"][0]
        self.assertEqual(send[send.index("--to") + 1], "hermes@kikin.helm")
        self.assertEqual(send[send.index("--in-reply-to") + 1], "<222.2.99@kikin.helm>")
        self.assertEqual(send[send.index("--subject") + 1], "Re: Wake test ABC")
        self.assertEqual(send[send.index("--from") + 1], "aura@honey.helm")
        self.assertIn(["receipt", "aura", "<222.2.99@kikin.helm>", "handling_completed"], fake.calls)

    def test_reply_sends_only_once_per_read(self):
        fake = Fake()
        run(self.mod, fake, "read next")
        run(self.mod, fake, "reply", b"one\n")
        code, err = run(self.mod, fake, "reply", b"two\n")
        self.assertEqual(code, 2)
        self.assertIn("already replied", err)
        self.assertEqual(len([c for c in fake.calls if c[0] == "send"]), 1)

    def test_failed_send_records_no_receipt_and_allows_a_retry(self):
        fake = Fake(send_rc=1)
        run(self.mod, fake, "read next")
        code, _ = run(self.mod, fake, "reply", b"x\n")
        self.assertEqual(code, 1)
        self.assertFalse([c for c in fake.calls if c[0] == "receipt"])
        self.assertFalse(json.load(open(self.mod.LAST))["replied"])

    def test_reply_without_a_read_or_with_arguments_is_refused(self):
        self.assertEqual(run(self.mod, Fake(), "reply", b"x\n")[0], 2)
        fake = Fake()
        run(self.mod, fake, "read next")
        self.assertEqual(run(self.mod, fake, "reply --to someone@kikin.helm", b"x\n")[0], 2)

    def test_reply_never_answers_her_own_mail(self):
        json.dump({"from": "aura@honey.helm", "message-id": "<1.2@kikin.helm>", "subject": "s", "replied": False},
                  open(self.mod.LAST, "w"))
        self.assertEqual(run(self.mod, Fake(), "reply", b"x\n")[0], 2)


if __name__ == "__main__":
    unittest.main()
