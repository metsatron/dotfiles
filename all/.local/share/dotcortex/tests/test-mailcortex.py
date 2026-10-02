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
        self.address = "reader@node-b.helm"
        self.maildir = self.root / "consorts/reader"
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

    def test_provision_is_private_idempotent_and_validates_before_writing(self) -> None:
        root = self.base / "fresh-mail"
        self.env["MAILCORTEX_ROOT"] = str(root)
        invalid = self.run_command("provision", "reader@node-b.helm", "../../escape")
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse(root.exists())
        for _ in range(2):
            result = self.run_command(
                "provision", "reader@node-b.helm", "seat+builder@node-a.helm"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        for directory in (
            root, root / "consorts", root / "consorts/reader",
            root / "seats", root / "seats/builder",
            *(root / "consorts/reader" / leaf for leaf in ("tmp", "new", "cur")),
            *(root / "seats/builder" / leaf for leaf in ("tmp", "new", "cur")),
        ):
            self.assertTrue(directory.is_dir(), directory)
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700, directory)
        self.assertEqual(list((root / "consorts/reader/new").iterdir()), [])
        sent = self.run_command(
            "send", "--from", "writer@node-a.helm", "--to", "reader@node-b.helm",
            "--subject", "Provisioned", "--body", "hello",
        )
        self.assertEqual(sent.returncode, 0, sent.stderr)
        self.assertEqual(len(list((root / "consorts/reader/new").iterdir())), 1)

    def test_provision_refuses_symlink_address(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        for leaf in ("tmp", "new", "cur"):
            (self.maildir / leaf).rmdir()
        self.maildir.rmdir()
        self.maildir.symlink_to(outside, target_is_directory=True)
        result = self.run_command("provision", self.address)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list(outside.iterdir()), [])

    def test_send_is_atomic_rfc822_delivery(self) -> None:
        result = self.run_command(
            "send",
            "--from", "sender@node-a.helm",
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
        self.assertEqual(message["From"], "sender@node-a.helm")
        self.assertEqual(message["To"], self.address)
        self.assertEqual(message["Subject"], "First post")
        self.assertTrue(message["Message-ID"])
        self.assertEqual(message.get_content().strip(), "Read LOGS/handoffs/example.md")
        self.assertFalse(message.is_multipart())

    def test_inbox_lists_and_read_moves_to_cur(self) -> None:
        sent = self.run_command(
            "send",
            "--from", "sender@node-a.helm",
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

    def test_inbox_skips_in_flight_sync_temp_files(self) -> None:
        (self.maildir / "new" / ".syncthing.123.host.tmp").write_bytes(b"Subject: partial\n\n")
        listing = self.run_command("inbox", self.address)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertNotIn(".syncthing", listing.stdout)

    def test_namespaces_and_input_guards(self) -> None:
        for address, expected in (
            ("writer@node-a.helm", "consorts/writer"),
            ("consort+writer@node-a.helm", "consorts/writer"),
            ("seat+builder@node-a.helm", "seats/builder"),
            ("machine+node-b@node-a.helm", "machines/node-b"),
            ("sanctuary+cde@node-a.helm", "sanctuaries/cde"),
        ):
            target = self.root / expected
            for leaf in ("tmp", "new", "cur"):
                (target / leaf).mkdir(parents=True, exist_ok=True)
            result = self.run_command("inbox", address)
            self.assertEqual(result.returncode, 0, (address, result.stderr))
        bad = self.run_command("inbox", "../../escape")
        self.assertEqual(bad.returncode, 2)
        missing = self.run_command("inbox", "unknown@node-a.helm")
        self.assertEqual(missing.returncode, 2)
        traversal = self.run_command("read", self.address, "../message")
        self.assertEqual(traversal.returncode, 2)


if __name__ == "__main__":
    unittest.main()
