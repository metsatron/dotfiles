"""The phone's StarFox receipt must not precede actual Kitten PCM."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


GATE = Path(__file__).resolve().parents[1] / "termux/.local/bin/pvox-pcm-start-gate"


class PcmStartGateTests(unittest.TestCase):
    def run_gate(self, pcm: bytes, identify: bool = True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt"
            receipt.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$PVOX_TEST_RECEIPTS"\n')
            receipt.chmod(0o700)
            env = os.environ.copy()
            env.update(PATH=f"{tmp}:{env['PATH']}", PVOX_TEST_RECEIPTS=str(root / "events"))
            if identify:
                env.update(PVOX_SPEAKER_ID="fable", PVOX_PLAYBACK_ID="play123")
            else:
                env.pop("PVOX_SPEAKER_ID", None)
                env.pop("PVOX_PLAYBACK_ID", None)
            (root / "pvox-speech-receipt").symlink_to(receipt)
            result = subprocess.run(
                [sys.executable, str(GATE)], input=pcm, capture_output=True, env=env, check=True
            )
            events = (root / "events").read_text().splitlines() if (root / "events").exists() else []
            return result.stdout, events

    def test_empty_and_silence_do_not_start(self):
        for pcm in (b"", b"\x00\x00" * 4000):
            with self.subTest(length=len(pcm)):
                self.assertEqual(self.run_gate(pcm), (pcm, []))

    def test_first_signal_starts_once_and_preserves_pcm(self):
        pcm = b"\x00\x00" * 3000 + b"\x01\x00" + b"\x00\x00" * 2000 + b"\xff\x7f"
        self.assertEqual(self.run_gate(pcm), (pcm, ["player_started fable play123"]))

    def test_unidentified_stream_remains_passthrough(self):
        pcm = b"\x01\x00" * 5000
        self.assertEqual(self.run_gate(pcm, identify=False), (pcm, []))


if __name__ == "__main__":
    unittest.main()
