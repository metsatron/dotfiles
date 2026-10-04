#!/usr/bin/env python3
"""Threading and opt-in Message-ID output fixtures for mailcortex."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


MAILCORTEX = os.environ.get("MAILCORTEX", "mailcortex")
OWNER = "owner@test.helm"
FACE = "seat+xmpp-bridge@test.helm"


class MailCortexCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = dict(os.environ,
                        MAILCORTEX_ROOT=str(self.tmp / "Mail"),
                        MAILCORTEX_RUNTIME=str(self.tmp / "state"))
        self.mc(["provision", OWNER, FACE])

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


if __name__ == "__main__":
    unittest.main()
