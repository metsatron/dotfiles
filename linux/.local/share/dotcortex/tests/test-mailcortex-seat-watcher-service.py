#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SERVICE = ROOT / "linux/.local/bin/mailcortex-seat-watcher-service"
UNIT = ROOT / "linux/.config/systemd/user/mailcortex-seat-watcher.service"
WATCHER = ROOT / "all/.local/bin/mailcortex-seat-watcher"
MAILCORTEX = ROOT / "all/.local/bin/mailcortex"


class SeatWatcherServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / ".local/bin"
        self.bin.mkdir(parents=True)
        shutil.copy2(SERVICE, self.bin / SERVICE.name)
        shutil.copy2(WATCHER, self.bin / WATCHER.name)
        shutil.copy2(MAILCORTEX, self.bin / MAILCORTEX.name)
        self.registry = self.home / ".config/mailcortex/seats.json"
        self.registry.parent.mkdir(parents=True)
        self.cron = self.home / "mailcortex-seat-watcher.cron"
        self.env = os.environ.copy() | {
            "HOME": str(self.home), "MAILCORTEX_TEST_INIT": "init",
            "MAILCORTEX_TEST_CRON_TARGET": str(self.cron),
            "MAILCORTEX_HOSTNAME": "fixture-host",
        }

    def run_service(self, *args, env=None):
        return subprocess.run([str(SERVICE), *args], env=env or self.env,
                              text=True, capture_output=True, check=False)

    def write_registry(self, *, target="fixture-private-target"):
        self.registry.write_text(json.dumps({
            "schema": "mailcortex.seats.v1", "host": "fixture-host",
            "seats": {"fixture-seat": {
                "host": "fixture-host", "mailbox": "seats/fixture-seat",
                "harness": "codex", "transport": "herdr",
                "herdr_session": "fixture-private-session",
                "herdr_target": target, "rate_limit_seconds": 0,
            }},
        }))
        self.registry.chmod(0o600)

    def test_help_and_dry_run_are_safe_without_registry(self):
        self.assertEqual(self.run_service("--help").returncode, 0)
        plan = self.run_service("--dry-run")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertIn("--run", plan.stdout)
        self.assertFalse(self.registry.exists())
        self.assertFalse(self.cron.exists())

    def test_absent_or_invalid_registry_never_installs_owner(self):
        self.assertEqual(self.run_service("--apply").returncode, 2)
        self.assertFalse(self.cron.exists())
        self.write_registry(target="")
        self.assertEqual(self.run_service("--apply").returncode, 2)
        self.assertFalse(self.cron.exists())
        self.write_registry()
        self.registry.chmod(0o644)
        self.assertEqual(self.run_service("--apply").returncode, 2)
        self.assertFalse(self.cron.exists())

    def test_unknown_init_refuses_before_registry_or_owner_actions(self):
        result = self.run_service("--apply", env=self.env | {"MAILCORTEX_TEST_INIT": "other"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported init", result.stderr)
        self.assertFalse(self.cron.exists())

    def test_sysv_apply_is_idempotent_and_contains_no_private_values(self):
        self.write_registry()
        first = self.run_service("--apply")
        self.assertEqual(first.returncode, 0, first.stderr)
        initial = self.cron.read_bytes()
        first_mtime = self.cron.stat().st_mtime_ns
        second = self.run_service("--apply")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.cron.read_bytes(), initial)
        self.assertEqual(self.cron.stat().st_mtime_ns, first_mtime)
        self.assertEqual(self.run_service("--check").returncode, 2)
        rendered = initial + UNIT.read_bytes() + SERVICE.read_bytes()
        self.assertIn(b"mailcortex-seat-watcher-service --run", rendered)
        self.assertIn(b"mailcortex-seat-watcher", rendered)
        self.assertIn(b".config/mailcortex/seats.json", rendered)
        self.assertNotIn(b"fixture-private-target", rendered)
        self.assertNotIn(b"fixture-private-session", rendered)
        self.assertNotIn(b"fixture-seat", rendered)

    def test_run_execs_watcher_with_separate_lifetime_lock_and_check_finds_it(self):
        self.write_registry()
        mailbox = self.home / "Mail/seats/fixture-seat"
        for leaf in ("new", "cur", "tmp"):
            (mailbox / leaf).mkdir(parents=True)
        self.assertEqual(self.run_service("--apply").returncode, 0)
        env = self.env | {
            "MAILCORTEX_ROOT": str(self.home / "Mail"),
            "MAILCORTEX_RUNTIME": str(self.home / "runtime"),
        }
        child = subprocess.Popen([str(SERVICE), "--run"], env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            pid_record = self.home / ".local/state/mailcortex/seat-watcher.pid"
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not pid_record.exists() and child.poll() is None:
                time.sleep(0.02)
            self.assertIsNone(child.poll(), "watcher exited before its first scan")
            self.assertEqual(pid_record.read_text().split()[0], str(child.pid))
            self.assertEqual(self.run_service("--check").returncode, 0)
            lifetime_lock = pid_record.with_name("seat-watcher-service.lock")
            with lifetime_lock.open("a+") as lock:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            scan_lock = self.home / "runtime/watcher.lock"
            while time.monotonic() < deadline and not scan_lock.exists() and child.poll() is None:
                time.sleep(0.02)
            self.assertTrue(scan_lock.exists(), "watcher never entered its scan loop")
        finally:
            child.terminate()
            child.wait(timeout=3)

    def test_systemd_unit_is_canonical_and_prevents_configuration_retries(self):
        unit = UNIT.read_text()
        self.assertIn("ExecStart=%h/.local/bin/mailcortex-seat-watcher-service --run", unit)
        self.assertIn("RestartPreventExitStatus=2", unit)
        self.assertIn("StartLimitBurst=3", unit)
        self.assertNotIn("fixture-private-target", unit)

    def test_systemd_apply_is_fixture_bound_and_idempotent(self):
        fake_bin = self.home / "fake-bin"
        fake_bin.mkdir()
        calls = self.home / "calls"
        enabled = self.home / "enabled"
        fake_systemctl = fake_bin / "systemctl"
        fake_systemctl.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" >> \"$MAILCORTEX_TEST_CALLS\"\n"
            "case \"$*\" in\n"
            "  *' show -P FragmentPath '*) printf '%s\\n' \"$HOME/.config/systemd/user/mailcortex-seat-watcher.service\" ;;\n"
            "  *' is-enabled '*) test -e \"$MAILCORTEX_TEST_ENABLED\" && echo enabled || echo disabled ;;\n"
            "  *' is-active --quiet '*) test -e \"$MAILCORTEX_TEST_ENABLED\" ;;\n"
            "  *' enable --now '*) touch \"$MAILCORTEX_TEST_ENABLED\" ;;\n"
            "esac\n")
        fake_systemctl.chmod(0o755)
        fake_sudo = fake_bin / "sudo"
        fake_sudo.write_text("#!/usr/bin/env bash\nprintf 'sudo %s\\n' \"$*\" >> \"$MAILCORTEX_TEST_CALLS\"\n")
        fake_sudo.chmod(0o755)
        fake_env = self.env | {
            "MAILCORTEX_TEST_INIT": "systemd", "MAILCORTEX_TEST_CALLS": str(calls),
            "MAILCORTEX_TEST_ENABLED": str(enabled),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        }
        absent = self.run_service("--apply", env=fake_env)
        self.assertEqual(absent.returncode, 2)
        self.assertNotIn("enable --now", calls.read_text())
        self.write_registry()
        first = self.run_service("--apply", env=fake_env)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.run_service("--apply", env=fake_env)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(calls.read_text().count("enable --now"), 1)


if __name__ == "__main__":
    unittest.main()
