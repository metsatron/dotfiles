from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve()
WATCHDOG = HERE.parents[3] / "bin" / "telegram-agent-watchdog"
HOST = socket.gethostname()

FAKE_MANAGER = """#!/usr/bin/env bash
root="$FAKE_ROOT"
case "$1" in
  enabled) cat "$root/enabled" ;;
  status) cat "$root/status"; [ ! -f "$root/status_fail" ] || exit 1 ;;
  start) echo "$2" >> "$root/starts"; echo "start:$2" >> "$root/calls"; if [ -f "$root/start_fail" ]; then exit 1; fi
         [ ! -f "$root/status_after_start" ] || cp "$root/status_after_start" "$root/status" ;;
  stop) echo "stop:$2" >> "$root/calls"; [ ! -f "$root/stop_fail" ] || exit 1 ;;
  *) exit 2 ;;
esac
"""


class WatchdogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manager = self.root / "manager"
        self.manager.write_text(FAKE_MANAGER)
        self.manager.chmod(self.manager.stat().st_mode | stat.S_IXUSR)
        (self.root / "enabled").write_text("ductor codex\n")
        self.set_status("RUNNING", "RUNNING")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def set_status(self, ductor: str, codex: str) -> None:
        (self.root / "status").write_text(
            "Host: x\nRunning processes:\n  ductor: %s\n  codex-helmastra (--telegram): %s\n" % (ductor, codex)
        )

    def run_watchdog(self, *extra: str, backoff: str = "0") -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(WATCHDOG), "--expected-host", HOST, "--manager", str(self.manager),
             "--state-dir", str(self.root / "state"), "--intent-dir", str(self.root / "intent"),
             "--boot-lock", str(self.root / "boot.lock"), "--spool", str(self.root / "spool"),
             "--pid-dir", str(self.root / "pids"), "--backoff", backoff, *extra],
            env=dict(os.environ, FAKE_ROOT=str(self.root)), text=True, capture_output=True, timeout=30,
        )

    def starts(self) -> list[str]:
        path = self.root / "starts"
        return path.read_text().split() if path.exists() else []

    def events(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted((self.root / "spool").glob("*.json"))]

    def test_healthy_agents_are_left_alone(self) -> None:
        result = self.run_watchdog()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.starts(), [])
        self.assertEqual(self.events(), [])

    def test_down_agent_is_relaunched_and_alerted(self) -> None:
        self.set_status("RUNNING", "STOPPED")
        self.run_watchdog()
        self.assertEqual(self.starts(), ["codex"])
        self.assertEqual([e["kind"] for e in self.events()], ["down"])
        self.set_status("RUNNING", "RUNNING")
        self.run_watchdog()
        self.assertEqual([e["kind"] for e in self.events()], ["down", "recovered"])
        self.assertEqual(self.events()[1]["severity"], "notice")

    def test_operator_stop_marker_is_respected(self) -> None:
        (self.root / "intent").mkdir()
        (self.root / "intent" / "codex").write_text("")
        self.set_status("RUNNING", "STOPPED")
        self.run_watchdog()
        self.assertEqual(self.starts(), [])

    def test_disabled_agent_is_never_touched(self) -> None:
        (self.root / "enabled").write_text("ductor\n")
        self.set_status("RUNNING", "STOPPED")
        self.run_watchdog()
        self.assertEqual(self.starts(), [])

    def test_unreadable_status_never_relaunches(self) -> None:
        (self.root / "status").write_text("Host: x\nnothing useful here\n")
        self.run_watchdog()
        self.assertEqual(self.starts(), [])
        self.assertEqual({e["kind"] for e in self.events()}, {"probe_unknown"})

    def test_empty_status_output_never_relaunches(self) -> None:
        (self.root / "status").write_text("")
        (self.root / "status_fail").write_text("")
        self.run_watchdog()
        self.assertEqual(self.starts(), [])

    def test_status_lines_are_read_even_when_the_status_call_exits_nonzero(self) -> None:
        # The real host exits 1 when any agent is degraded; the other agents' lines still count.
        self.set_status("RUNNING", "STOPPED")
        (self.root / "status_fail").write_text("")
        self.run_watchdog()
        self.assertEqual(self.starts(), ["codex"])

    def test_attempt_cap_holds_and_alerts_once(self) -> None:
        self.set_status("RUNNING", "STOPPED")
        (self.root / "start_fail").write_text("")
        for _ in range(6):
            self.run_watchdog("--max-attempts", "2")
        self.assertEqual(self.starts(), ["codex", "codex"])
        kinds = [e["kind"] for e in self.events()]
        self.assertEqual(kinds.count("down"), 1)
        self.assertEqual(kinds.count("relaunch_failed"), 1)

    def test_backoff_blocks_immediate_retry(self) -> None:
        self.set_status("RUNNING", "STOPPED")
        (self.root / "start_fail").write_text("")
        self.run_watchdog(backoff="3600")
        self.run_watchdog(backoff="3600")
        self.assertEqual(self.starts(), ["codex"])

    def request(self, agent: str, requester_pid: int, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(WATCHDOG), "request", agent, "--requester-pid", str(requester_pid),
             "--state-dir", str(self.root / "state"), "--pid-dir", str(self.root / "pids")],
            env=dict(os.environ, **(env or {})), text=True, capture_output=True, timeout=30,
        )

    def calls(self) -> list[str]:
        path = self.root / "calls"
        return path.read_text().split() if path.exists() else []

    def dead_pid(self) -> int:
        proc = subprocess.Popen(["true"])
        proc.wait()
        return proc.pid

    def test_revive_waits_for_the_requesting_turn_to_detach(self) -> None:
        holder = subprocess.Popen(["sleep", "30"])
        try:
            self.assertEqual(self.request("codex", holder.pid).returncode, 0)
            self.run_watchdog()
            self.assertEqual(self.calls(), [])
            self.assertTrue((self.root / "state/requests/codex.json").exists())
        finally:
            holder.kill()
            holder.wait()

    def test_revive_stops_then_starts_externally_after_detach(self) -> None:
        (self.root / "status_after_start").write_text("Host: x\n  ductor: RUNNING\n  codex-helmastra (--telegram): RUNNING\n")
        self.request("codex", self.dead_pid())
        self.run_watchdog()
        self.assertEqual(self.calls(), ["stop:codex", "start:codex"])
        self.assertEqual([e["kind"] for e in self.events()], ["revive_done"])
        self.assertFalse((self.root / "state/requests/codex.json").exists())

    def test_revive_request_is_idempotent(self) -> None:
        holder = subprocess.Popen(["sleep", "30"])
        try:
            self.request("codex", holder.pid)
            second = self.request("codex", holder.pid)
            self.assertEqual(second.returncode, 0)
            self.assertIn("already pending", second.stdout)
            self.assertEqual(len(list((self.root / "state/requests").glob("*.json"))), 1)
        finally:
            holder.kill()
            holder.wait()

    def test_revive_cooldown_refuses_a_second_revive(self) -> None:
        (self.root / "status_after_start").write_text("Host: x\n  ductor: RUNNING\n  codex-helmastra (--telegram): RUNNING\n")
        self.request("codex", self.dead_pid())
        self.run_watchdog()
        self.request("codex", self.dead_pid())
        self.run_watchdog()
        self.assertEqual(self.calls(), ["stop:codex", "start:codex"])
        self.assertEqual([e["kind"] for e in self.events()], ["revive_done", "revive_rejected"])

    def test_stale_generation_is_dropped_without_restart(self) -> None:
        (self.root / "pids").mkdir()
        holder = subprocess.Popen(["sleep", "30"])
        try:
            (self.root / "pids/codex-helmastra-telegram.pid").write_text(str(holder.pid))
            self.request("codex", self.dead_pid())
            holder.kill()
            holder.wait()
            successor = subprocess.Popen(["sleep", "30"])
            try:
                (self.root / "pids/codex-helmastra-telegram.pid").write_text(str(successor.pid))
                self.run_watchdog()
            finally:
                successor.kill()
                successor.wait()
        finally:
            holder.kill()
        self.assertEqual(self.calls(), [])
        self.assertEqual([e["kind"] for e in self.events()], ["revive_stale"])

    def test_failed_revive_clears_the_stop_marker_so_healing_continues(self) -> None:
        (self.root / "intent").mkdir()
        (self.root / "intent/codex").write_text("")
        (self.root / "start_fail").write_text("")
        self.request("codex", self.dead_pid())
        self.run_watchdog()
        self.assertFalse((self.root / "intent/codex").exists())
        self.assertIn("revive_failed", [e["kind"] for e in self.events()])

    def test_request_is_self_targeted_by_default(self) -> None:
        refused = self.request("ductor", self.dead_pid(), env={"TELEGRAM_AGENT_SELF": "codex"})
        self.assertEqual(refused.returncode, 2)
        self.assertFalse((self.root / "state/requests/ductor.json").exists())

    def test_wrong_host_refuses(self) -> None:
        result = subprocess.run([str(WATCHDOG), "--expected-host", "not-" + HOST, "--manager", str(self.manager)],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 1)

    def test_help_is_side_effect_free(self) -> None:
        result = subprocess.run([str(WATCHDOG), "--help"], text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
