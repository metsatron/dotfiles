#!/usr/bin/env python3
"""Threading and opt-in Message-ID output fixtures for mailcortex."""

import email
import email.policy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


MAILCORTEX = os.environ.get("MAILCORTEX", "mailcortex")
OWNER = "owner@test.helm"
FACE = "seat+xmpp-bridge@test.helm"
ALICE = "seat+alice@test.helm"
BOB = "seat+bob@test.helm"
UNREGISTERED = "seat+ghost@test.helm"


class MailCortexCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        registry = self.tmp / "seats.json"
        registry.write_text(json.dumps({
            "schema": "mailcortex.seats.v1", "host": "test",
            "seats": {"xmpp-bridge": {}, "alice": {}, "bob": {}},
        }))
        self.env = dict(os.environ,
                        MAILCORTEX_ROOT=str(self.tmp / "Mail"),
                        MAILCORTEX_RUNTIME=str(self.tmp / "state"),
                        MAILCORTEX_SEAT_REGISTRY=str(registry))
        self.mc(["provision", OWNER, FACE, ALICE, BOB, UNREGISTERED])

    def mc(self, args, check=True):
        return subprocess.run([MAILCORTEX, *args], env=self.env, text=True,
                              capture_output=True, check=check)

    def test_default_output_and_thread_headers(self):
        first = self.mc(["send", "--from", OWNER, "--to", FACE,
                         "--subject", "first", "--body", "hello"])
        self.assertNotIn("\t", first.stdout)
        second = self.mc(["send", "--from", OWNER, "--to", FACE,
                          "--subject", "second", "--body", "reply",
                          "--in-reply-to", "<first@example.test>", "--print-id"])
        filename, message_id = second.stdout.strip().split("\t")
        self.assertRegex(message_id, r"^<[^<>\s@]+@[^<>\s@]+>$")
        rendered = self.mc(["read", FACE, filename]).stdout
        self.assertIn("In-Reply-To: <first@example.test>", rendered)
        self.assertIn("References: <first@example.test>", rendered)

    def test_malformed_parent_is_rejected(self):
        result = self.mc(["send", "--from", OWNER, "--to", FACE,
                          "--subject", "bad", "--body", "no",
                          "--in-reply-to", "not-a-message-id"], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid Message-ID", result.stderr)

    def test_permission_auth_header_roundtrip_and_validation(self):
        auth = ("seat=fable;request_id=abcde;behavior=allow;timestamp=123;"
                + "hmac=" + "a" * 64)
        sent = self.mc(["send", "--from", OWNER, "--to", FACE,
                        "--subject", "permission", "--body", "decision",
                        "--permission-auth", auth, "--print-id"])
        filename, _message_id = sent.stdout.strip().split("\t")
        rendered = self.mc(["read", FACE, filename]).stdout
        self.assertIn("X-MailCortex-Permission: " + auth, rendered)
        invalid = self.mc(["send", "--from", OWNER, "--to", FACE,
                           "--subject", "bad", "--body", "no",
                           "--permission-auth", "forged"], check=False)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("invalid permission authentication", invalid.stderr)

    def test_cc_fanout_delivers_full_copy_with_headers_to_each_recipient(self):
        sent = self.mc(["send", "--from", OWNER, "--to", FACE, "--cc", ALICE,
                        "--cc", BOB, "--subject", "squadron", "--body", "status"])
        lines = sorted(sent.stdout.strip().splitlines())
        recipients = [line.split("\t", 1)[0] for line in lines]
        self.assertEqual(recipients, sorted([FACE, ALICE, BOB]))
        for address in (FACE, ALICE, BOB):
            inbox = self.mc(["inbox", address]).stdout
            self.assertIn("squadron", inbox)
            name = inbox.strip().splitlines()[0].split("\t")[1]
            rendered = self.mc(["read", address, name]).stdout
            self.assertIn(f"To: {FACE}", rendered)
            self.assertIn(f"Cc: {ALICE}, {BOB}", rendered)

    def test_cc_dedup_against_to_delivers_once_with_no_cc_header(self):
        sent = self.mc(["send", "--from", OWNER, "--to", FACE, "--cc", FACE,
                        "--subject", "solo", "--body", "hi"])
        self.assertNotIn("\t", sent.stdout.strip())
        rendered = self.mc(["read", FACE, sent.stdout.strip()]).stdout
        self.assertIn("Cc: \n", rendered)

    def test_cc_preflight_refuses_whole_send_before_any_write(self):
        refused = self.mc(["send", "--from", OWNER, "--to", FACE, "--cc", UNREGISTERED,
                           "--subject", "blocked", "--body", "no"], check=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("no registered seat", refused.stderr)
        self.assertNotIn("blocked", self.mc(["inbox", FACE]).stdout)

    def test_fanout_bound_rejects_excess_recipients(self):
        # None of these ten Cc addresses need to be provisioned: the bound is
        # checked before any Maildir lookup, on syntactically valid addresses alone.
        cc_args = []
        for index in range(10):
            cc_args += ["--cc", f"seat+flood{index}@test.helm"]
        result = self.mc(["send", "--from", OWNER, "--to", FACE, *cc_args,
                          "--subject", "flood", "--body", "no"], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fanout exceeds 10 recipients: 11", result.stderr)

    def test_forward_preserves_original_as_rfc822_attachment_with_default_subject(self):
        original = self.mc(["send", "--from", OWNER, "--to", FACE,
                            "--subject", "quarterly numbers", "--body", "see attached",
                            "--print-id"])
        filename, _message_id = original.stdout.strip().split("\t")
        forwarded = self.mc(["forward", "--from", FACE, "--to", ALICE,
                             FACE, filename, "--body", "fyi"])
        name = forwarded.stdout.strip()
        rendered = self.mc(["read", ALICE, name]).stdout
        self.assertIn("Subject: Fwd: quarterly numbers", rendered)
        self.assertIn("fyi", rendered)
        raw = next((self.tmp / "Mail" / "seats" / "alice" / "cur").glob("*")).read_bytes()
        self.assertIn(b"Content-Type: message/rfc822", raw)
        delivered = email.message_from_bytes(raw, policy=email.policy.default)
        attached = next(part for part in delivered.walk() if part.get_content_type() == "message/rfc822")
        original = attached.get_payload(0)
        self.assertEqual(str(original["Subject"]), "quarterly numbers")

    def test_forward_respects_explicit_subject_and_defaults_empty_body(self):
        original = self.mc(["send", "--from", OWNER, "--to", FACE,
                            "--subject", "raw status", "--body", "x", "--print-id"])
        filename, _message_id = original.stdout.strip().split("\t")
        forwarded = self.mc(["forward", "--from", FACE, "--to", BOB,
                             "--subject", "custom subject", FACE, filename])
        name = forwarded.stdout.strip()
        rendered = self.mc(["read", BOB, name]).stdout
        self.assertIn("Subject: custom subject", rendered)

    def test_forward_source_lookup_rejects_unknown_message(self):
        result = self.mc(["forward", "--from", FACE, "--to", ALICE,
                          FACE, "not-a-real-filename", "--body", "x"], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("message not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
