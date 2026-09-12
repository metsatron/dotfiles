from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve()
BOOT = HERE.parents[3] / "bin" / "telegram-agent-boot"
CRON_APPLY = HERE.parents[3] / "bin" / "telegram-agent-boot-cron-apply"
MANAGER = HERE.parents[3] / "bin" / "telegram-agent-host"
HOST = subprocess.check_output(["hostname"], text=True).strip()


class TelegramAgentBootTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.manager = self.root / "manager"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_manager(self, succeed_after: int) -> None:
        self.manager.write_text(
            "#!/bin/sh\n"
            f"count_file={str(self.root / 'count')!r}\n"
            "count=0\n"
            "[ ! -f \"$count_file\" ] || count=$(cat \"$count_file\")\n"
            "count=$((count + 1))\n"
            "printf '%s\\n' \"$count\" >\"$count_file\"\n"
            f"[ \"$count\" -ge {succeed_after} ]\n",
            encoding="utf-8",
        )
        self.manager.chmod(self.manager.stat().st_mode | stat.S_IXUSR)

    def run_boot(self, *extra: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(self.root)
        env["TELEGRAM_AGENT_BOOT_NO_LOG"] = "1"
        return subprocess.run(
            [str(BOOT), "--expected-host", HOST, "--delay", "0", "--retry-seconds", "0",
             "--manager", str(self.manager), "--state-dir", str(self.state), *extra],
            text=True, capture_output=True, env=env, timeout=10,
        )

    def test_retry_then_ready_receipt(self) -> None:
        self.write_manager(succeed_after=2)
        result = self.run_boot("--attempts", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "count").read_text().strip(), "2")
        receipt = json.loads((self.state / "receipt.json").read_text())
        self.assertEqual((receipt["status"], receipt["attempt"], receipt["host"]), ("ready", 2, HOST.lower()))

    def test_exhaustion_is_loud_and_durable(self) -> None:
        self.write_manager(succeed_after=9)
        result = self.run_boot("--attempts", "2")
        self.assertEqual(result.returncode, 1)
        receipt = json.loads((self.state / "receipt.json").read_text())
        self.assertEqual((receipt["status"], receipt["attempt"]), ("failed", 2))

    def test_wrong_host_refuses_before_state_or_manager(self) -> None:
        self.write_manager(succeed_after=1)
        result = subprocess.run(
            [str(BOOT), "--expected-host", "definitely-not-this-host", "--delay", "0",
             "--manager", str(self.manager), "--state-dir", str(self.state)],
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 64)
        self.assertFalse(self.state.exists())
        self.assertFalse((self.root / "count").exists())

    def test_lock_prevents_duplicate_launch(self) -> None:
        self.write_manager(succeed_after=1)
        self.state.mkdir(parents=True)
        with (self.state / "boot.lock").open("w") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_boot("--attempts", "1")
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.root / "count").exists())

    def test_help_is_side_effect_free(self) -> None:
        result = subprocess.run([str(BOOT), "--help"], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        self.assertFalse(self.state.exists())

    def test_cron_dry_run_is_exact_and_non_mutating(self) -> None:
        result = subprocess.run(
            [str(CRON_APPLY), "--host", HOST, "--dry-run"],
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("@reboot", result.stdout)
        self.assertIn("telegram-agent-boot --expected-host " + HOST, result.stdout)

    def test_manager_help_is_side_effect_free(self) -> None:
        home = self.root / "help-home"
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["XDG_STATE_HOME"] = str(home / "state")
        for flag in ("-h", "--help"):
            result = subprocess.run([str(MANAGER), flag], text=True, capture_output=True, env=env, timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Usage:", result.stdout)
            self.assertFalse((home / "state").exists())


if __name__ == "__main__":
    unittest.main()
