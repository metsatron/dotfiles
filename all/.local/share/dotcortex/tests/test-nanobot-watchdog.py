"""The Nano watchdog must require stable ownership and a persistent NFS wait."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest import mock
import shutil

WATCHDOG = Path(__file__).resolve().parents[3] / "bin/nanobot-watchdog"
loader = importlib.machinery.SourceFileLoader("nanobot_watchdog", str(WATCHDOG))
spec = importlib.util.spec_from_loader(loader.name, loader)
watchdog = importlib.util.module_from_spec(spec)
loader.exec_module(watchdog)


class NanoWatchdogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="nano-watchdog-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config"
        self.proc = self.root / "proc"
        (self.config / "run").mkdir(parents=True)
        (self.config / "logs").mkdir()
        self.pid = 4123
        self.ticks = 87234
        self.log = self.config / "logs/gateway.abc123.log"
        self.log.write_text("last event\n", encoding="utf-8")
        self.owner = self.config / "run/gateway.abc123.json"
        self.owner.write_text(json.dumps({
            "pid": self.pid, "identity": f"{self.pid}:{self.ticks}",
            "config_path": str(self.config / "config.json"),
            "log_path": str(self.log),
            "command": ["/opt/nano/bin/python", "-m", "nanobot", "gateway",
                        "--foreground", "--config", str(self.config / "config.json")],
        }), encoding="utf-8")
        task = self.proc / str(self.pid) / "task" / str(self.pid)
        task.mkdir(parents=True)
        (self.proc / str(self.pid) / "stat").write_text(
            f"{self.pid} (nanobot-gateway) " + " ".join(["S"] + ["0"] * 18 + [str(self.ticks)] + ["0"] * 8),
            encoding="utf-8",
        )
        (self.proc / str(self.pid) / "cmdline").write_bytes(b"nanobot-gateway\0")
        (task / "status").write_text("State:\tD (disk sleep)\n", encoding="utf-8")
        (task / "wchan").write_text("rpc_wait_bit_killable\n", encoding="utf-8")

    def snapshot(self):
        return watchdog.inspect(self.config, self.proc)

    def add_search_worker(self, pid: int = 4222, ticks: int = 99001) -> Path:
        worker = self.proc / str(pid)
        task = worker / "task" / str(pid)
        task.mkdir(parents=True)
        fields = ["D", str(self.pid), str(pid), str(pid)] + ["0"] * 15 + [str(ticks)] + ["0"] * 8
        (worker / "stat").write_text(
            f"{pid} (nanobot-search) " + " ".join(fields), encoding="utf-8"
        )
        (worker / "comm").write_text("nanobot-search\n", encoding="utf-8")
        (worker / "cmdline").write_bytes(b"python\0--multiprocessing-fork\0")
        (task / "status").write_text("State:\tD (disk sleep)\n", encoding="utf-8")
        (task / "wchan").write_text("rpc_wait_bit_killable\n", encoding="utf-8")
        return worker

    def configure_alert(self, recipients=None) -> tuple[str, str]:
        token = "PRIVATE_TEST_TOKEN"
        recipient = "PRIVATE_TEST_RECIPIENT"
        (self.config / "config.json").write_text(json.dumps({
            "channels": {"telegram": {"enabled": True, "token": token}},
        }), encoding="utf-8")
        (self.config / "pairing.json").write_text(json.dumps({
            "approved": {"telegram": [recipient] if recipients is None else recipients},
        }), encoding="utf-8")
        return token, recipient

    def alert_args(self):
        return watchdog.parser().parse_args([
            "--expected-host", socket.gethostname(), "--config-dir", str(self.config),
            "--proc-root", str(self.proc), "--state-path", str(self.root / "state.json"),
            "--manager", str(self.root / "fake-manager"),
        ])

    def test_local_alert_route_and_mocked_send(self) -> None:
        token, recipient = self.configure_alert()
        self.assertEqual(watchdog.alert_route(self.config), (token, recipient))
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = b'{"ok": true}'
        with mock.patch.object(watchdog, "urlopen") as opener:
            opener.return_value.__enter__.return_value = response
            watchdog.alert(self.alert_args(), {}, self.root / "events.jsonl",
                           "recovered", "Nano recovered")
            self.assertEqual(opener.call_count, 1)
            self.assertEqual(opener.call_args.kwargs["timeout"], 5)
        ledger_text = (self.root / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn('"telegram_delivery": "sent"', ledger_text)
        self.assertNotIn(token, ledger_text)
        self.assertNotIn(recipient, ledger_text)
        for recipients in ([], [recipient, "ANOTHER_RECIPIENT"]):
            self.configure_alert(recipients)
            with self.assertRaisesRegex(ValueError, "telegram-recipient-cardinality"):
                watchdog.alert_route(self.config)

    def test_alert_route_resolves_only_the_private_env_token_placeholder(self) -> None:
        token, recipient = self.configure_alert()
        config = json.loads((self.config / "config.json").read_text(encoding="utf-8"))
        config["channels"]["telegram"]["token"] = "${TELEGRAM_BOT_TOKEN}"
        (self.config / "config.json").write_text(json.dumps(config), encoding="utf-8")
        (self.config / "env").write_text(
            "IGNORED=something\nTELEGRAM_BOT_TOKEN=" + token + "\n",
            encoding="utf-8",
        )
        self.assertEqual(watchdog.alert_route(self.config), (token, recipient))

    def test_network_error_is_sanitized_without_hiding_recovery(self) -> None:
        token, recipient = self.configure_alert()
        before, _ = self.snapshot()
        after = {**before, "pid": self.pid + 1, "ticks": self.ticks + 1}
        def manager(_path, verb, _timeout):
            if verb == "stop":
                shutil.rmtree(self.proc / str(self.pid))
            return subprocess.CompletedProcess([], 0, "", "")
        with mock.patch.object(watchdog, "run_manager", side_effect=manager), \
             mock.patch.object(watchdog, "inspect", side_effect=[(before, "ok"), (after, "ok")]), \
             mock.patch.object(watchdog, "urlopen", side_effect=OSError(f"{token} {recipient}")):
            result = watchdog.recover(self.alert_args(), before, {}, self.root / "events.jsonl")
        self.assertEqual(result["status"], "recovered")
        ledger_text = (self.root / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn('"action": "recovered"', ledger_text)
        self.assertIn('"telegram_delivery": "failed"', ledger_text)
        self.assertIn('"error_class": "OSError"', ledger_text)
        self.assertNotIn(token, ledger_text)
        self.assertNotIn(recipient, ledger_text)

    def test_requires_same_process_and_unchanged_log_for_five_minutes(self) -> None:
        first, reason = self.snapshot()
        self.assertEqual(reason, "ok")
        result, state = watchdog.assess(first, reason, {}, 1000, 300, 900, 3)
        self.assertEqual(result["status"], "suspect")
        result, state = watchdog.assess(first, reason, state, 1299, 300, 900, 3)
        self.assertEqual(result["status"], "suspect")
        result, state = watchdog.assess(first, reason, state, 1300, 300, 900, 3)
        self.assertEqual(result["status"], "recover")
        self.log.write_text("new event\n", encoding="utf-8")
        changed, reason = self.snapshot()
        result, _ = watchdog.assess(changed, reason, state, 1301, 300, 900, 3)
        self.assertEqual(result["status"], "suspect")

    def test_rejects_wrong_wait_channel_and_owner_reuse(self) -> None:
        (self.proc / str(self.pid) / "task" / str(self.pid) / "wchan").write_text("io_schedule", encoding="utf-8")
        current, reason = self.snapshot()
        result, _ = watchdog.assess(current, reason, {}, 1000, 300, 900, 3)
        self.assertEqual(result["status"], "healthy")
        owner = json.loads(self.owner.read_text(encoding="utf-8"))
        owner["identity"] = "4123:1"
        self.owner.write_text(json.dumps(owner), encoding="utf-8")
        current, reason = self.snapshot()
        self.assertIsNone(current)
        self.assertEqual(reason, "owner-pid-reused")

    def test_persistent_owned_search_worker_is_signalled_without_gateway_restart(self) -> None:
        gateway_task = self.proc / str(self.pid) / "task" / str(self.pid)
        (gateway_task / "status").write_text("State:\tS (sleeping)\n", encoding="utf-8")
        (gateway_task / "wchan").write_text("futex_wait_queue\n", encoding="utf-8")
        self.add_search_worker()
        current, reason = self.snapshot()
        self.assertEqual(reason, "ok")
        self.assertEqual(current["blocked_worker"]["pid"], 4222)
        result, state = watchdog.assess(current, reason, {}, 1000, 300, 900, 3)
        self.assertEqual(result["status"], "suspect")
        result, state = watchdog.assess(current, reason, state, 1300, 300, 900, 3)
        self.assertEqual(result["status"], "terminate-worker")
        args = self.alert_args()
        with mock.patch.object(watchdog.os, "killpg") as killpg, \
             mock.patch.object(watchdog, "alert"), \
             mock.patch.object(watchdog, "run_manager") as manager:
            outcome = watchdog.terminate_worker(
                args, current, state, self.root / "events.jsonl"
            )
        killpg.assert_called_once_with(4222, watchdog.signal.SIGKILL)
        manager.assert_not_called()
        self.assertEqual(outcome["status"], "worker-termination-requested")
        self.assertTrue((self.proc / str(self.pid)).exists())

    def test_dry_run_never_creates_state_or_calls_manager(self) -> None:
        args = watchdog.parser().parse_args([
            "--expected-host", socket.gethostname(), "--config-dir", str(self.config),
            "--proc-root", str(self.proc), "--state-path", str(self.root / "missing/state.json"),
            "--manager", str(self.root / "must-not-run"), "--dry-run",
        ])
        result = watchdog.run(args, now=1000)
        self.assertEqual(result["status"], "suspect")
        self.assertFalse((self.root / "missing").exists())

    def test_recovery_stops_exact_nano_before_start_and_refuses_failed_stop(self) -> None:
        before, _ = self.snapshot()
        args = watchdog.parser().parse_args([
            "--expected-host", socket.gethostname(), "--config-dir", str(self.config),
            "--proc-root", str(self.proc), "--state-path", str(self.root / "state.json"),
            "--manager", str(self.root / "fake-manager"),
        ])
        calls = []

        def manager(_path, verb, _timeout):
            calls.append(verb)
            if verb == "stop":
                shutil.rmtree(self.proc / str(self.pid))
            return subprocess.CompletedProcess([], 0, "", "")

        after = {**before, "pid": self.pid + 1, "ticks": self.ticks + 1}
        with mock.patch.object(watchdog, "run_manager", side_effect=manager), \
             mock.patch.object(watchdog, "inspect", side_effect=[(before, "ok"), (after, "ok")]):
            result = watchdog.recover(args, before, {}, self.root / "events.jsonl")
        self.assertEqual(calls, ["stop", "start"])
        self.assertEqual(result["status"], "recovered")

        calls.clear()
        with mock.patch.object(watchdog, "run_manager", side_effect=lambda _p, verb, _t: (calls.append(verb), subprocess.CompletedProcess([], 1, "", ""))[1]), \
             mock.patch.object(watchdog, "inspect", return_value=(before, "ok")):
            result = watchdog.recover(args, before, {}, self.root / "events.jsonl")
        self.assertEqual(calls, ["stop"])
        self.assertEqual(result["reason"], "nano-did-not-stop")


if __name__ == "__main__":
    unittest.main()
