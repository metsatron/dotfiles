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

    def write_manager(self, failures: dict[str, int]) -> None:
        encoded = json.dumps(failures, sort_keys=True)
        self.manager.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            f"root = pathlib.Path({str(self.root)!r})\n"
            f"failures = {encoded!r}\n"
            "failures = json.loads(failures)\n"
            "if sys.argv[1:] == ['enabled']:\n"
            "    print('ductor codex opencode')\n"
            "    raise SystemExit(0)\n"
            "if len(sys.argv) != 3 or sys.argv[1] != 'start':\n"
            "    raise SystemExit(2)\n"
            "agent = sys.argv[2]\n"
            "calls = root / 'calls'\n"
            "with calls.open('a', encoding='utf-8') as stream:\n"
            "    stream.write(agent + '\\n')\n"
            "count_file = root / ('count-' + agent)\n"
            "count = int(count_file.read_text()) if count_file.exists() else 0\n"
            "count += 1\n"
            "count_file.write_text(str(count))\n"
            "raise SystemExit(1 if count <= int(failures.get(agent, 0)) else 0)\n",
            encoding="utf-8",
        )
        self.manager.chmod(self.manager.stat().st_mode | stat.S_IXUSR)

    def run_boot(self, *extra: str) -> subprocess.CompletedProcess[str]:
        env = {
            "HOME": str(self.root),
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "XDG_STATE_HOME": str(self.root / "xdg-state"),
            "TELEGRAM_AGENT_BOOT_NO_LOG": "1",
        }
        return subprocess.run(
            [str(BOOT), "--expected-host", HOST, "--delay", "0", "--retry-seconds", "0",
             "--manager", str(self.manager), "--state-dir", str(self.state), *extra],
            text=True, capture_output=True, env=env, timeout=10,
        )

    def test_retry_then_ready_receipt(self) -> None:
        self.write_manager({"ductor": 1})
        result = self.run_boot("--attempts", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "calls").read_text().splitlines(), ["ductor", "codex", "opencode", "ductor"])
        receipt = json.loads((self.state / "receipt.json").read_text())
        self.assertEqual((receipt["status"], receipt["attempt"], receipt["host"]), ("ready", 2, HOST.lower()))
        self.assertEqual(receipt["schema"], "dotcortex.telegram-agent-boot.v2")
        self.assertEqual(receipt["agents"], {"ductor": "ready", "codex": "ready", "opencode": "ready"})

    def test_children_inherit_group_umask_state_stays_private(self) -> None:
        # Agents write cortex-shared repos: a 077 leaking from the boot script
        # closed every file the bot fleet created (2026-09-25).
        self.write_manager({})
        text = self.manager.read_text()
        self.manager.write_text(text.replace(
            "agent = sys.argv[2]\n",
            "agent = sys.argv[2]\n"
            "import os\n"
            "mask = os.umask(0); os.umask(mask)\n"
            "(root / 'umask').write_text(oct(mask))\n", 1))
        result = subprocess.run(
            ["sh", "-c", 'umask 077; exec "$@"', "sh", str(BOOT), "--expected-host", HOST,
             "--delay", "0", "--retry-seconds", "0", "--attempts", "1",
             "--manager", str(self.manager), "--state-dir", str(self.state)],
            text=True, capture_output=True, timeout=10,
            env={"HOME": str(self.root), "PATH": "/usr/local/bin:/usr/bin:/bin",
                 "TELEGRAM_AGENT_BOOT_NO_LOG": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "umask").read_text(), "0o2")
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)

    def test_exhaustion_is_loud_and_durable(self) -> None:
        self.write_manager({"ductor": 9})
        result = self.run_boot("--attempts", "2")
        self.assertEqual(result.returncode, 1)
        receipt = json.loads((self.state / "receipt.json").read_text())
        self.assertEqual((receipt["status"], receipt["attempt"]), ("failed", 2))
        self.assertEqual(receipt["agents"], {"ductor": "failed", "codex": "ready", "opencode": "ready"})
        self.assertEqual((self.root / "calls").read_text().splitlines(), ["ductor", "codex", "opencode", "ductor"])

    def test_wrong_host_refuses_before_state_or_manager(self) -> None:
        self.write_manager({})
        result = subprocess.run(
            [str(BOOT), "--expected-host", "definitely-not-this-host", "--delay", "0",
             "--manager", str(self.manager), "--state-dir", str(self.state)],
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 64)
        self.assertFalse(self.state.exists())
        self.assertFalse((self.root / "calls").exists())

    def test_lock_prevents_duplicate_launch(self) -> None:
        self.write_manager({})
        self.state.mkdir(parents=True)
        with (self.state / "boot.lock").open("w") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_boot("--attempts", "1")
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.root / "calls").exists())

    def test_boot_lock_not_inherited_by_spawned_child(self) -> None:
        # A daemonized agent must never inherit the boot lock (fd 9). If it does,
        # the flock stays held for the agent's whole lifetime and every later boot
        # -- including the self-heal cron -- fails flock -n and skips the spawn.
        # The manager is a shell that backgrounds a lingering child WITHOUT closing
        # fds (mimicking the real host); Python's own Popen would auto-close fds and
        # hide the very leak this guards against.
        self.state.mkdir(parents=True)
        pid_file = self.root / "child.pid"
        self.manager.write_text(
            "#!/usr/bin/env bash\n"
            'case "$1" in\n'
            "  enabled) echo one ;;\n"
            # Detach the child's stdio from the captured pipe (else run_boot blocks
            # on it for 30s); fd 9 is untouched, so the inheritance check stays valid.
            f'  start) sleep 30 </dev/null >/dev/null 2>&1 & echo "$!" > {str(pid_file)!r} ;;\n'
            "esac\n",
            encoding="utf-8",
        )
        self.manager.chmod(self.manager.stat().st_mode | stat.S_IXUSR)
        result = self.run_boot("--attempts", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        child = int(pid_file.read_text().strip())
        try:
            fd_dir = Path("/proc") / str(child) / "fd"
            holders = []
            if fd_dir.exists():
                for fd in fd_dir.iterdir():
                    try:
                        target = os.readlink(str(fd))
                    except OSError:
                        continue
                    if target.rsplit("/", 1)[-1] == "boot.lock":
                        holders.append((fd.name, target))
            self.assertEqual(holders, [], "spawned child inherited the boot lock: %r" % (holders,))
        finally:
            try:
                os.kill(child, 9)
            except ProcessLookupError:
                pass

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
        self.assertIn("/.guix-extra-profiles/core/core/bin:", result.stdout)

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
