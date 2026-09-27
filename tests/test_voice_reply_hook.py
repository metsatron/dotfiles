"""Keep the detached voice relay shell boundary parseable at runtime."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "all/.local/bin/claude-hook-voice-reply"


class VoiceReplyHookTests(unittest.TestCase):
    def test_voice_payload_reaches_detached_worker_without_shell_expansion_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_setsid = root / "setsid"
            fake_setsid.write_text('#!/bin/sh\nprintf "%s\\n" "$1" > "$TEST_SETSID_LOG"\n')
            fake_setsid.chmod(0o755)
            receipt = root / "setsid-args"
            env = {**os.environ, "PATH": f"{root}:{os.environ['PATH']}",
                   "XDG_CACHE_HOME": directory, "TEST_SETSID_LOG": str(receipt),
                   "CLAUDE_WARM_HERDR_AGENT": "auryn"}
            result = subprocess.run(
                [str(HOOK)], input=json.dumps({"tool_input": {"text": "Voice check"}}),
                text=True, capture_output=True, env=env, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            deadline = time.monotonic() + 2
            while not receipt.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(receipt.read_text().strip(), "bash")


if __name__ == "__main__":
    unittest.main()
