#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
COMMAND = ROOT / "all/.local/bin/mailcortex"


class MailCortexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.root = self.base / "Mail"
        self.env = os.environ | {"MAILCORTEX_ROOT": str(self.root)}
        self.address = "helmductor@x230.helm"
        self.maildir = self.root / "consorts/helmductor"
        for leaf in ("tmp", "new", "cur"):
            (self.maildir / leaf).mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_command(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(COMMAND), *args],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_help_is_side_effect_free(self) -> None:
        empty_root = self.base / "absent"
        result = subprocess.run(
            [str(COMMAND), "--help"],
            env=self.env | {"MAILCORTEX_ROOT": str(empty_root)},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(empty_root.exists())

    def test_send_is_atomic_rfc822_delivery(self) -> None:
        result = self.run_command(
            "send",
            "--from", "fable@kikin.helm",
            "--to", self.address,
            "--subject", "First post",
            "--body", "Read LOGS/handoffs/example.md\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list((self.maildir / "tmp").iterdir()), [])
        delivered = list((self.maildir / "new").iterdir())
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0].name, result.stdout.strip())
        self.assertEqual(delivered[0].stat().st_mode & 0o777, 0o600)
        message = BytesParser(policy=policy.default).parsebytes(delivered[0].read_bytes())
        self.assertEqual(message["From"], "fable@kikin.helm")
        self.assertEqual(message["To"], self.address)
        self.assertEqual(message["Subject"], "First post")
        self.assertTrue(message["Message-ID"])
        self.assertEqual(message.get_content().strip(), "Read LOGS/handoffs/example.md")
        self.assertFalse(message.is_multipart())

    def test_inbox_lists_and_read_moves_to_cur(self) -> None:
        sent = self.run_command(
            "send",
            "--from", "fable@kikin.helm",
            "--to", self.address,
            "--subject", "Move me",
            "--body", "hello",
        )
        name = sent.stdout.strip()
        listing = self.run_command("inbox", self.address)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn(f"new\t{name}\t", listing.stdout)
        read = self.run_command("read", self.address, name)
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertIn("Subject: Move me", read.stdout)
        self.assertIn("\n\nhello\n", read.stdout)
        self.assertFalse((self.maildir / "new" / name).exists())
        self.assertTrue((self.maildir / "cur" / (name + ":2,S")).exists())

    def test_namespaces_and_input_guards(self) -> None:
        for address, expected in (
            ("fable@kikin.helm", "consorts/fable"),
            ("consort+fable@kikin.helm", "consorts/fable"),
            ("seat+builder@kikin.helm", "seats/builder"),
            ("machine+x230@kikin.helm", "machines/x230"),
            ("sanctuary+cde@kikin.helm", "sanctuaries/cde"),
        ):
            target = self.root / expected
            for leaf in ("tmp", "new", "cur"):
                (target / leaf).mkdir(parents=True, exist_ok=True)
            result = self.run_command("inbox", address)
            self.assertEqual(result.returncode, 0, (address, result.stderr))
        bad = self.run_command("inbox", "../../escape")
        self.assertEqual(bad.returncode, 2)
        missing = self.run_command("inbox", "unknown@kikin.helm")
        self.assertEqual(missing.returncode, 2)
        traversal = self.run_command("read", self.address, "../message")
        self.assertEqual(traversal.returncode, 2)


if __name__ == "__main__":
    unittest.main()
