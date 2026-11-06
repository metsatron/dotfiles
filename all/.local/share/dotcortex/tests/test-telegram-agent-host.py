from __future__ import annotations

import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import tempfile
import time
import unittest
from unittest import mock


HERE = Path(__file__).resolve()
MANAGER = HERE.parents[3] / "bin" / "telegram-agent-host"
HOST = subprocess.check_output(["hostname"], text=True).strip().lower()


class HermesReviewerSafetyTests(unittest.TestCase):
    def shell(self, names, script):
        text = MANAGER.read_text()
        functions = "\n".join(name + "() {" + text.split(name + "() {", 1)[1].split("\n}\n", 1)[0] + "\n}" for name in names)
        with tempfile.TemporaryDirectory() as root:
            return subprocess.run(["bash", "-c", "set -euo pipefail\nSTATE_DIR=" + root + "\nHOME=$STATE_DIR\nINTENT_DIR=$STATE_DIR/intent\nKNOWN_AGENTS=hermes\n" + functions + "\n" + script],
                                  env={"PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=5)

    def test_record_drift_cannot_prove_predecessor_exit(self):
        names = ["hermes_wait_generation_exit", "hermes_stop_unlocked", "recover_hermes"]
        for record in ("", "434343:200"):
            for action in ("stop", "restart"):
                with self.subTest(record=record, action=action):
                    script = """
record=$STATE_DIR/record
printf '%s' '424242:100' > "$record"
hermes_gateway_pid() { local v; v=$(cat "$record"); if [ "${1:-}" = identity ]; then echo "$v"; else echo "${v%%:*}"; fi; }
hermes_proc_identity() { echo '424242:100'; }
hermes_service_installed() { return 1; }
ps() { echo 1; }
kill() { printf '%s' "$DRIFT" > "$record"; echo signal; }
hermes_signal_identity() { kill; }
hermes_inspect() { return 1; }
hermes_preflight() { return 0; }
hermes_running() { return 0; }
python3() { return 0; }
hermes_start_unlocked() { echo UNSAFE_REPLACEMENT; }
HERMES_STOP_EXIT_TIMEOUT=0
""" + "DRIFT=" + repr(record) + "\n" + ("hermes_stop_unlocked" if action == "stop" else "recover_hermes restart")
                    result = self.shell(names, script)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("signal", result.stdout, result.stderr)
                    self.assertNotIn("UNSAFE_REPLACEMENT", result.stdout)

    def test_bulk_stop_propagates_hermes_lock_refusal(self):
        names = ["stop_all", "stop_agent", "validate_agent", "stop_hermes", "hermes_lifecycle_lock", "hermes_lifecycle_unlock", "mark_intentional_stop"]
        script = """
orig=$(declare -f stop_agent); eval "${orig/stop_agent/real_stop_agent}"
stop_agent() { if [ "$1" = hermes ]; then real_stop_agent "$1"; else return 0; fi; }
hermes_stop_unlocked() { echo UNSAFE_EFFECT; }
exec 9>"$STATE_DIR/hermes-recovery.lock"
flock -n 9
rc=0
stop_all || rc=$?
[ ! -f "$INTENT_DIR/hermes" ] || { echo FALSE_MARKER; exit 99; }
exit "$rc"
"""
        result = self.shell(names, script)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("FALSE_MARKER", result.stdout)
        self.assertNotIn("UNSAFE_EFFECT", result.stdout)
        self.assertNotIn("hermes stopped", result.stdout)
        self.assertNotIn("All agents stopped", result.stdout)

    def test_direct_conditional_stop_propagates_failure(self):
        for rc in (1, 75):
            result = self.shell(["stop_agent", "validate_agent"], "stop_hermes() { return " + str(rc) + "; }; if stop_agent hermes; then exit 0; else exit $?; fi")
            self.assertEqual(result.returncode, rc, result.stdout + result.stderr)
            self.assertNotIn("hermes stopped", result.stdout)

    def test_direct_signal_uses_generation_bound_handle(self):
        text = MANAGER.read_text()
        code = text.split("hermes_signal_identity() {", 1)[1].split("<<'PYCODE'\n", 1)[1].split("\nPYCODE", 1)[0]
        for ticks, expected in (("200", False), ("100", True)):
            fields = ["S"] + ["0"] * 18 + [ticks]
            with self.subTest(ticks=ticks), mock.patch("sys.argv", ["signal", "424242:100", "TERM"]), \
                 mock.patch("os.pidfd_open", return_value=91, create=True), \
                 mock.patch.object(Path, "read_text", return_value="424242 (fixture) " + " ".join(fields)), \
                 mock.patch("signal.pidfd_send_signal", create=True) as sent, \
                 mock.patch("os.close") as closed, mock.patch("os.kill") as numeric:
                if expected:
                    exec(compile(code, "signal-fixture", "exec"), {})
                    sent.assert_called_once_with(91, signal.SIGTERM)
                else:
                    with self.assertRaises(SystemExit) as failure:
                        exec(compile(code, "signal-fixture", "exec"), {})
                    self.assertEqual(failure.exception.code, 75)
                    sent.assert_not_called()
                closed.assert_called_once_with(91)
                numeric.assert_not_called()

    def test_pid_reuse_is_a_different_predecessor_generation(self):
        result = self.shell(["hermes_wait_generation_exit"], "hermes_gateway_pid() { echo 424242:100; }; hermes_proc_identity() { echo 424242:200; }; hermes_wait_generation_exit 424242:100 0")
        self.assertEqual(result.returncode, 0, result.stderr)


class TelegramAgentHostColdStartTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.state = self.root / "state"
        self.agents = self.root / "agents"
        self.bin = self.home / ".local/bin"
        self.forge_bin = self.home / "HelmCortex/FORGE/bin"
        self.core_bin = self.home / ".guix-extra-profiles/core/core/bin"
        for directory in (self.home, self.state, self.agents, self.bin, self.forge_bin, self.core_bin):
            directory.mkdir(parents=True)
        self.write_executable("ductor", "#!/bin/sh\ntrap 'exit 0' TERM INT\nwhile :; do sleep 1; done\n")
        self.write_executable("node", "#!/bin/sh\nexit 0\n", directory=self.core_bin)
        # Every fixture process this test spawns directly is registered here
        # with its kernel start ticks. Cleanup only ever signals a registered,
        # identity-validated, isolated process group it owns itself.
        self._owned: list[tuple[subprocess.Popen, str]] = []

    # -- kill-safety helpers (Fable 2026-10-09 three-kill night; hardened
    #    2026-10-25 after the recurrent gateway SIGTERM) ---------------------
    # A pid file left by a failed test may contain anything. os.killpg treats
    # its argument as a process-GROUP id, so a file-read pid whose value
    # collides with a live group (any session-leader daemon: the gateway, the
    # coordinator, another agent) is a SIGTERM to that whole bystander group.
    # Never signal a group from a pid file alone: validate an owned Popen, the
    # exact kernel start ticks, and an isolated group this fixture created.

    def _stat_fields(self, pid: int) -> list[str] | None:
        try:
            return Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
        except OSError:
            return None

    def _proc_ticks(self, pid: int) -> str | None:
        fields = self._stat_fields(pid)
        if fields is None or fields[0] == "Z":
            return None
        return fields[19]

    def _proc_pgid(self, pid: int) -> int | None:
        # /proc/<pid>/stat after "pid (comm)": [0]=state [1]=ppid [2]=pgrp
        # [3]=session ... [19]=starttime. pgrp is overall field 5 -> index 2.
        fields = self._stat_fields(pid)
        if fields is None or fields[0] == "Z":
            return None
        try:
            return int(fields[2])
        except (IndexError, ValueError):
            return None

    def _proc_cmdline(self, pid: int) -> str:
        try:
            return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            return ""

    def _is_ancestor(self, pid: int) -> bool:
        ancestor = os.getpid()
        while ancestor > 1:
            if ancestor == pid:
                return True
            fields = self._stat_fields(ancestor)
            if fields is None:
                return False
            try:
                ancestor = int(fields[1])
            except (IndexError, ValueError):
                return False
        return False

    def _owns_isolated_group(self, proc: subprocess.Popen, ticks: str) -> bool:
        """True only when proc is still the exact fixture process and the
        leader of its own isolated process group that is not ours."""
        pid = proc.pid
        if pid <= 1 or pid == os.getpid():
            return False
        if self._is_ancestor(pid):
            return False
        if self._proc_ticks(pid) != str(ticks):
            return False  # stale or recycled: never signal an unknown process
        pgid = self._proc_pgid(pid)
        if pgid != pid:
            return False  # not an isolated group leader (inherited our group)
        if pgid == os.getpgid(0):
            return False  # our own group: would signal the coordinator
        return True

    def register_owned(self, proc: subprocess.Popen) -> subprocess.Popen:
        ticks = self._proc_ticks(proc.pid)
        self._owned.append((proc, ticks if ticks is not None else ""))
        self.addCleanup(self.terminate_owned_group, proc)
        return proc

    def terminate_owned_group(self, proc: subprocess.Popen) -> bool:
        """SIGTERM then bounded SIGKILL of an isolated fixture group we own.

        Returns True when the group is gone or was signalled; returns False
        (and signals nothing) when ownership cannot be proven -- a bystander,
        stale/recycled pid, parent/ancestor, or our own group is never touched.
        """
        entry = next((item for item in self._owned if item[0] is proc), None)
        if entry is None:
            return False  # not a fixture process this test registered
        if not self._owns_isolated_group(proc, entry[1]):
            return False
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            return True
        try:
            proc.wait(timeout=5)
            return True
        except subprocess.TimeoutExpired:
            pass
        if self._owns_isolated_group(proc, entry[1]):
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return True

    def _cleanup_pid_file_child(self, pid_file: Path) -> None:
        """Signal only a pidfd-bound fixture child, never a numeric PID.

        A unique fixture-root argv establishes fixture ownership, not kernel
        identity. Open the handle before inspecting argv and revalidate start
        ticks afterwards. Reuse after validation cannot retarget the handle.
        Unsupported pidfds fail closed (no unsafe numeric fallback).
        """
        try:
            recorded_pid = int(pid_file.read_text())
        except (OSError, ValueError):
            return
        if recorded_pid <= 1 or recorded_pid == os.getpid() or self._is_ancestor(recorded_pid):
            return
        ticks = self._proc_ticks(recorded_pid)
        if ticks is None:
            return
        fd = None
        try:
            fd = os.pidfd_open(recorded_pid, 0)
            if str(self.root) not in self._proc_cmdline(recorded_pid):
                return
            if self._proc_ticks(recorded_pid) != ticks:
                return
            signal.pidfd_send_signal(fd, signal.SIGTERM)
        except (OSError, AttributeError):
            pass
        finally:
            if fd is not None:
                os.close(fd)

    def test_pidfile_cleanup_is_identity_bound(self):
        pidfile = self.root / "cleanup.pid"
        pidfile.write_text("424242")
        for ticks, expected in ((("100", "200"), False), (("100", "100"), True)):
            with self.subTest(ticks=ticks), mock.patch.object(self, "_is_ancestor", return_value=False), \
                 mock.patch.object(self, "_proc_ticks", side_effect=ticks), \
                 mock.patch.object(self, "_proc_cmdline", return_value=str(self.root / "owned-fixture")), \
                 mock.patch("os.pidfd_open", return_value=91, create=True) as opened, \
                 mock.patch("signal.pidfd_send_signal", create=True) as sent, \
                 mock.patch("os.close") as closed, mock.patch("os.kill") as numeric:
                self._cleanup_pid_file_child(pidfile)
                numeric.assert_not_called()
                opened.assert_called_once_with(424242, 0)
                closed.assert_called_once_with(91)
                if expected:
                    sent.assert_called_once_with(91, signal.SIGTERM)
                else:
                    sent.assert_not_called()

    def test_pidfile_cleanup_refuses_without_pidfd(self):
        pidfile = self.root / "cleanup.pid"
        pidfile.write_text("424242")
        with mock.patch.object(self, "_is_ancestor", return_value=False), \
             mock.patch.object(self, "_proc_ticks", return_value="100"), \
             mock.patch.object(self, "_proc_cmdline", return_value=str(self.root)), \
             mock.patch("os.pidfd_open", side_effect=OSError("unsupported"), create=True), \
             mock.patch("os.kill") as numeric:
            self._cleanup_pid_file_child(pidfile)
            numeric.assert_not_called()

    def tearDown(self) -> None:
        if hasattr(self, "fixture_gateway_cleanup"):
            self.fixture_gateway_cleanup()
        # Reap manager-spawned fixture children by single-pid, cmdline-validated
        # SIGTERM only. Never os.killpg a pid read from a file: killpg's
        # argument is a group id, and a stale/recycled value would SIGTERM a
        # bystander group (the 2026-10-25 recurrent gateway SIGTERM class).
        for pid_file in (
            self.state / "telegram-agents/ductor-supervise.pid",
            self.state / "telegram-agents/codex-helmastra-telegram.pid",
            self.state / "gemma-pi-telegram/adapter.pid",
            self.state / "vibe-telegram/adapter.pid",
        ):
            if pid_file.exists():
                self._cleanup_pid_file_child(pid_file)
        self.temp.cleanup()

    def read_start_ticks(self, pid: int) -> str:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
        return fields[19]

    def write_dsh_marker(
        self,
        pid: int,
        *,
        start_ticks: str | None = None,
        profile: str = "helmcortex-telegram",
        generation: str = "0123456789abcdef0123456789abcdef",
        expected_generation: str | None = None,
    ) -> None:
        marker_base = self.state / "telegram-agents/deepseek-harness.ready"
        marker = marker_base.with_name(f"{marker_base.name}.{generation}")
        marker.parent.mkdir(parents=True, exist_ok=True)
        (marker.parent / "deepseek-harness.generation").write_text(
            expected_generation if expected_generation is not None else generation,
            encoding="utf-8",
        )
        marker.write_text(json.dumps({
            "schema": 1,
            "component": "dsh-telegram",
            "pid": pid,
            "start_ticks": start_ticks if start_ticks is not None else self.read_start_ticks(pid),
            "profile": profile,
            "generation": generation,
            "provider": "neuralwatt",
            "model": "deepseek-v4.1-flash-flex",
            "telegram_bot_identity_validated": True,
            "long_polling_owned": True,
            "ready_at": "2026-09-17T00:00:00Z",
        }), encoding="utf-8")

    def write_executable(self, name: str, body: str, directory: Path | None = None) -> None:
        path = (directory or self.bin) / name
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def environment(self, timeout: int) -> dict[str, str]:
        env = {
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.state),
            "DOTCORTEX_AGENTS_DIR": str(self.agents),
            "PATH": str(self.bin) + os.pathsep + "/usr/local/bin:/usr/bin:/bin",
            "DUCTOR_HOME_DIR": str(self.root / "ductor-home"),
            "DUCTOR_READY_TIMEOUT": str(timeout),
            "DSH_TELEGRAM_ENV_FILE": str(self.home / ".config/deepseek-harness-telegram/env"),
            "DSH_HOME": str(self.home / ".local/share/deepseek-harness-telegram/dsh-home"),
        }
        return env

    def run_manager(self, *args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(MANAGER), *args], text=True, capture_output=True,
                              env=self.environment(timeout), timeout=timeout + 5)

    def prepare_codex_supervisor(self, stop_delay: float = 1.5) -> subprocess.Popen[bytes]:
        scripts = self.home / "HelmCortex/FORGE/scripts"
        scripts.mkdir(parents=True)
        adapter = scripts / "codex_telegram.py"
        adapter.write_text(
            "import signal, time\n"
            "signal.signal(signal.SIGTERM, lambda *_: exit(0))\n"
            "while True: time.sleep(1)\n",
            encoding="utf-8",
        )
        supervisor = scripts / "codex_supervisor.py"
        supervisor.write_text(
            "import fcntl, os, pathlib, signal, subprocess, sys, time\n"
            "state = pathlib.Path(os.environ['XDG_STATE_HOME']) / 'telegram-agents'\n"
            "state.mkdir(parents=True, exist_ok=True)\n"
            "pid_file = state / 'codex-helmastra-telegram.pid'\n"
            "ready_file = state / 'codex-helmastra-telegram.ready'\n"
            "child_file = state / 'codex-helmastra-telegram.child.ready'\n"
            "lock = (state / 'codex-helmastra-telegram.supervisor.lock').open('a+')\n"
            "fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            "child = subprocess.Popen([sys.executable, str(pathlib.Path(__file__).with_name('codex_telegram.py'))])\n"
            "pid_file.write_text(str(os.getpid()) + '\\n')\n"
            "ready_file.write_text(str(os.getpid()) + '\\n')\n"
            "child_file.write_text(str(child.pid) + '\\n')\n"
            "def stop(*_):\n"
            "    ready_file.unlink(missing_ok=True)\n"
            "    child_file.unlink(missing_ok=True)\n"
            "    child.terminate()\n"
            "    time.sleep(float(os.environ.get('CODEX_TEST_STOP_DELAY', '0.1')))\n"
            "    raise SystemExit(0)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "while child.poll() is None: time.sleep(0.1)\n",
            encoding="utf-8",
        )
        wrapper = self.forge_bin / "codex-helmastra"
        wrapper.write_text(
            "#!/usr/bin/env python3\n"
            "import fcntl, os, pathlib, subprocess, sys, time\n"
            "state = pathlib.Path(os.environ['XDG_STATE_HOME']) / 'telegram-agents'\n"
            "lock_path = state / 'codex-helmastra-telegram.supervisor.lock'\n"
            "with lock_path.open('a+') as lock:\n"
            "    try: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            "    except BlockingIOError:\n"
            "        print('supervisor lock is still held', file=sys.stderr)\n"
            "        raise SystemExit(73)\n"
            f"supervisor = {str(supervisor)!r}\n"
            "process = subprocess.Popen([sys.executable, supervisor], stdin=subprocess.DEVNULL, "
            "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)\n"
            "pid_file = state / 'codex-helmastra-telegram.pid'\n"
            "ready_file = state / 'codex-helmastra-telegram.ready'\n"
            "child_file = state / 'codex-helmastra-telegram.child.ready'\n"
            "for _ in range(100):\n"
            "    if (pid_file.exists() and ready_file.exists() and child_file.exists() "
            "and pid_file.read_text().strip() == str(process.pid) "
            "and ready_file.read_text().strip() == str(process.pid)):\n"
            "        raise SystemExit(0)\n"
            "    if process.poll() is not None: break\n"
            "    time.sleep(0.02)\n"
            "raise SystemExit(1)\n",
            encoding="utf-8",
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
        env = self.environment(2)
        env["CODEX_TEST_STOP_DELAY"] = str(stop_delay)
        process = subprocess.Popen(
            ["python3", str(supervisor)], env=env, start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        ready_file = self.state / "telegram-agents/codex-helmastra-telegram.ready"
        child_file = self.state / "telegram-agents/codex-helmastra-telegram.child.ready"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (ready_file.exists() and child_file.exists()):
            time.sleep(0.02)
        self.assertTrue(ready_file.exists() and child_file.exists(), "fixture supervisor did not become ready")
        self.register_owned(process)
        return process

    def test_codex_stop_waits_for_supervisor_after_readiness_disappears(self) -> None:
        old_supervisor = self.prepare_codex_supervisor()
        try:
            stopped = self.run_manager("stop", "codex", timeout=4)
            self.assertEqual(stopped.returncode, 0, stopped.stderr)

            # The supervisor removes readiness immediately on TERM but deliberately
            # retains its exclusive launch lock while winding down. A correct stop
            # must wait for that exact process, so an immediate start can acquire it.
            started = self.run_manager("start", "codex", timeout=4)
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            old_supervisor.wait(timeout=2)
            replacement = int(
                (self.state / "telegram-agents/codex-helmastra-telegram.pid").read_text()
            )
            self.assertNotEqual(replacement, old_supervisor.pid)
        finally:
            if old_supervisor.poll() is None:
                # Owned, isolated, tick-validated group signal only.
                self.terminate_owned_group(old_supervisor)
                old_supervisor.wait(timeout=5)

    def test_cold_supervisor_waits_for_delayed_child(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|ductor\n", encoding="utf-8")
        self.write_executable(
            "ductor-supervise",
            "#!/bin/sh\n"
            "d=$XDG_STATE_HOME/telegram-agents\nmkdir -p \"$d\"\n"
            "printf '%s\\n' $$ >\"$d/ductor-supervise.pid\"\n"
            "sleep 2\nductor & child=$!\nprintf '%s\\n' $child >\"$d/ductor-child.pid\"\nwait $child\n",
            directory=self.forge_bin,
        )
        result = self.run_manager("start", "ductor", timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ductor started", result.stdout)

    def test_start_all_attempts_later_agent_after_ductor_failure(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|ductor,pi-agent\n", encoding="utf-8")
        gemma_env = self.home / ".config/gemma-pi-telegram/.env"
        gemma_env.parent.mkdir(parents=True)
        gemma_env.write_text("TELEGRAM_BOT_TOKEN=fake\nTELEGRAM_ALLOWED_USER_ID=1\n", encoding="utf-8")
        gemma_env.chmod(0o600)
        fake_adapter = self.home / "gemma_telegram.py"
        fake_adapter.write_text("import time\nwhile True: time.sleep(1)\n", encoding="utf-8")
        self.write_executable(
            "gemma-pi-telegram",
            f"#!/bin/sh\n"
            "d=$XDG_STATE_HOME/gemma-pi-telegram\nmkdir -p \"$d\"\n"
            "printf '%s\\n' $$ >\"$d/adapter.pid\"\n"
            f"exec python3 {str(fake_adapter)!r}\n",
            directory=self.forge_bin,
        )
        self.write_executable(
            "ductor-supervise",
            "#!/bin/sh\n"
            "d=$XDG_STATE_HOME/telegram-agents\nmkdir -p \"$d\"\n"
            "printf '%s\\n' $$ >\"$d/ductor-supervise.pid\"\n"
            "trap 'exit 0' TERM INT\nwhile :; do sleep 1; done\n",
            directory=self.forge_bin,
        )
        result = self.run_manager("start", timeout=1)
        self.assertEqual(result.returncode, 1)
        self.assertIn("pi-agent started", result.stdout)
        self.assertIn("Failed to start enabled agent: ductor", result.stderr)

    def test_targeted_pi_agent_status_is_parseable_without_other_agents(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|pi-agent\n", encoding="utf-8")
        gemma_env = self.home / ".config/gemma-pi-telegram/.env"
        gemma_env.parent.mkdir(parents=True)
        gemma_env.write_text("TELEGRAM_BOT_TOKEN=fake\nTELEGRAM_ALLOWED_USER_ID=1\n", encoding="utf-8")
        gemma_env.chmod(0o600)
        fake_adapter = self.home / "gemma_telegram.py"
        fake_adapter.write_text("import time\nwhile True: time.sleep(1)\n", encoding="utf-8")
        self.write_executable(
            "gemma-pi-telegram",
            f"#!/bin/sh\n"
            "d=$XDG_STATE_HOME/gemma-pi-telegram\nmkdir -p \"$d\"\n"
            "printf '%s\\n' $$ >\"$d/adapter.pid\"\n"
            f"exec python3 {str(fake_adapter)!r}\n",
            directory=self.forge_bin,
        )

        started = self.run_manager("start", "pi-agent", timeout=2)
        self.assertEqual(started.returncode, 0, started.stderr)
        status = self.run_manager("status", "pi-agent", timeout=2)

        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertRegex(status.stdout, r"^pi-agent: RUNNING pid=\d+ \(gemma-pi-telegram\)\n$")
        self.assertNotIn("opencode", status.stdout)

    def prepare_nanobot_wrapper(self, *, emit_ready: bool = True, stale_ready: bool = False) -> None:
        workspace = self.home / "HelmCortex/FORGE/brain/nanobot"
        workspace.mkdir(parents=True)
        config_dir = self.home / ".config/nanobot-telegram"
        config_dir.mkdir(parents=True)
        config_dir.joinpath("config.json").write_text("{}\n", encoding="utf-8")
        config_dir.joinpath("env").write_text(
            "TELEGRAM_BOT_TOKEN=123456789:abcdefghijklmnopqrstuvwxyzABCDE\n",
            encoding="utf-8",
        )
        log_file = config_dir / "gateway.log"
        if stale_ready:
            log_file.write_text(
                "telegram | bot @helmcortex_nano_bot connected\n", encoding="utf-8"
            )
        running = config_dir / "running"
        ready_command = (
            "printf '%s\\n' 'telegram | bot @helmcortex_nano_bot connected' >>\"$log\""
            if emit_ready else ":"
        )
        self.write_executable(
            "nanobot-telegram",
            "#!/bin/sh\n"
            f"running={str(running)!r}\n"
            f"log={str(log_file)!r}\n"
            "case \"$1:$2\" in\n"
            "  gateway:status)\n"
            "    if [ -f \"$running\" ]; then printf 'Running: yes\\nPID: 4242\\n'; else printf 'Running: no\\n'; fi\n"
            # Nanobot's rich renderer wraps long paths beneath the label in a
            # narrow terminal; reproduce that real output shape here.
            "    printf 'Logs:\\n%s\\n' \"$log\"\n"
            "    ;;\n"
            "  gateway:--background)\n"
            "    : >\"$running\"\n"
            f"    {ready_command}\n"
            "    ;;\n"
            "  gateway:stop) rm -f \"$running\" ;;\n"
            "  *) exit 2 ;;\n"
            "esac\n",
        )

    def test_nanobot_targeted_lifecycle_uses_scoped_wrapper(self) -> None:
        self.prepare_nanobot_wrapper()
        started = self.run_manager("start", "nanobot", timeout=2)
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertIn("connected as @helmcortex_nano_bot", started.stdout)

        status = self.run_manager("status", "nanobot", timeout=2)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(
            status.stdout,
            "nanobot: RUNNING pid=4242 (@helmcortex_nano_bot)\n",
        )

        stopped = self.run_manager("stop", "nanobot", timeout=2)
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        status = self.run_manager("status", "nanobot", timeout=2)
        self.assertEqual(status.returncode, 1)
        self.assertIn("nanobot: STOPPED", status.stdout)

    def start_gateway_stand_in(self, *, ticks: str | None = None, record: bool = True) -> subprocess.Popen[bytes]:
        # Own isolated session so fixture cleanup can signal exactly this
        # group and never the test runner's (coordinator's) group.
        gateway = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.register_owned(gateway)
        if record:
            hermes_home = self.home / ".hermes"
            hermes_home.mkdir(exist_ok=True)
            (hermes_home / "gateway.pid").write_text(json.dumps({
                "pid": gateway.pid,
                "kind": "hermes-gateway",
                "argv": ["hermes_cli/main.py", "gateway", "run"],
                "start_time": ticks if ticks is not None else self.read_start_ticks(gateway.pid),
            }), encoding="utf-8")
        return gateway

    def hermes_config(self, config=None):
        home = self.home / ".hermes"
        home.mkdir(exist_ok=True)
        (home / "config.yaml").write_text(json.dumps(config if config is not None else {
            "model": {"provider": "openai-codex", "default": "fixture-model"},
            "platforms": {"telegram": {"enabled": True, "token": "fixture-token"}},
        }))

    def test_hermes_connected_transport_does_not_verify_reply_credentials(self):
        gateway = self.ready_hermes()
        result = self.run_manager("status", "hermes")
        self.assertEqual(result.returncode, 69, result.stdout + result.stderr)
        self.assertIn("UNKNOWN", result.stdout)
        self.assertIn("reply credential usability NOT-VERIFIED", result.stdout)
        self.assertNotIn("RUNNING", result.stdout)
        self.assertIsNone(gateway.poll())

    def test_hermes_cold_boot_discard_is_rejected_before_stop(self):
        gateway = self.ready_hermes()
        result = self.run_manager("preflight", "hermes")
        self.assertEqual(result.returncode, 78, result.stdout + result.stderr)
        self.assertIn("queued-input retention", result.stdout)
        self.assertIsNone(gateway.poll())

    def test_hermes_retention_alone_does_not_authorize_runtime_mutation(self):
        self.ready_hermes()
        path = self.home / ".hermes/config.yaml"
        config = json.loads(path.read_text())
        config["platforms"]["telegram"]["extra"] = {"drop_pending_on_cold_boot": False}
        path.write_text(json.dumps(config))
        result = self.run_manager("preflight", "hermes")
        self.assertEqual(result.returncode, 69, result.stdout + result.stderr)
        self.assertIn("native startup dependencies and capability continuity NOT-VERIFIED", result.stdout)

    def test_hermes_adoption_gate_preserves_degraded_predecessor(self):
        gateway = self.ready_hermes(gateway_state="degraded")
        path = self.home / ".hermes/config.yaml"
        config = json.loads(path.read_text())
        config["platforms"]["telegram"]["extra"] = {"drop_pending_on_cold_boot": False}
        path.write_text(json.dumps(config))
        marker = self.root / "unsafe-start"
        self.write_executable("hermes", f"#!/bin/sh\ntouch {marker}\nexit 99\n")
        result = self.run_manager("recover", "hermes")
        self.assertEqual(result.returncode, 69, result.stdout + result.stderr)
        self.assertIsNone(gateway.poll())
        self.assertFalse(marker.exists(), "unverified native startup must never execute")

    def test_hermes_unknown_reply_path_is_never_restarted(self):
        gateway = self.ready_hermes()
        result = self.run_manager("recover", "hermes")
        self.assertEqual(result.returncode, 69, result.stdout + result.stderr)
        self.assertIsNone(gateway.poll())

    def test_hermes_cron_only_cannot_bypass_enabled_telegram_adoption(self):
        gateway = self.ready_hermes()
        original_environment = self.environment
        self.environment = lambda timeout: dict(original_environment(timeout), HERMES_GATEWAY_MODE="cron-only")
        result = self.run_manager("restart", "hermes")
        self.assertEqual(result.returncode, 78, result.stdout + result.stderr)
        self.assertIsNone(gateway.poll())

    def test_hermes_missing_reply_route_is_blocked_not_running(self):
        self.start_gateway_stand_in()
        self.hermes_config({"platforms": {"telegram": {"enabled": True, "token": "fixture-token"}}})
        result = self.run_manager("status", "hermes")
        self.assertIn("hermes gateway run: BLOCKED", result.stdout)
        self.assertNotEqual(result.returncode, 0)

    def ready_hermes(self, **updates):
        gateway = self.start_gateway_stand_in()
        self.hermes_config()
        home = self.home / ".hermes"
        state = json.loads((home / "gateway.pid").read_text())
        state.update(gateway_state="running", active_agents=0, platforms={"telegram": {
            "state": "connected", "writer_pid": gateway.pid,
            "writer_start_time": self.read_start_ticks(gateway.pid),
        }})
        state.update(updates)
        (home / "gateway_state.json").write_text(json.dumps(state))
        return gateway

    def test_hermes_missing_telegram_preflight_preserves_generation(self):
        gateway = self.ready_hermes()
        self.hermes_config({"model": {"provider": "openai-codex", "default": "fixture-model"}})
        result = self.run_manager("recover", "hermes")
        self.assertEqual(result.returncode, 78, result.stdout + result.stderr)
        self.assertIsNone(gateway.poll())
        self.assertIn("Telegram configuration unavailable", result.stdout)

    def test_hermes_healthy_recover_does_not_restart(self):
        gateway = self.ready_hermes(active_agents=2)
        self.hermes_config({})
        original_environment = self.environment
        self.environment = lambda timeout: dict(original_environment(timeout), HERMES_GATEWAY_MODE="cron-only")
        result = self.run_manager("recover", "hermes")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIsNone(gateway.poll())

    def test_hermes_stale_telegram_writer_is_not_ready(self):
        self.ready_hermes(platforms={"telegram": {"state": "connected", "writer_pid": 1,
                                                "writer_start_time": "1"}})
        status = self.run_manager("status", "hermes")
        self.assertNotEqual(status.returncode, 0)
        self.assertNotIn("RUNNING", status.stdout)
        self.assertNotIn("opencode", status.stdout)

    def test_hermes_stale_unconfigured_platform_does_not_poison_telegram(self):
        gateway = self.ready_hermes()
        path = self.home / ".hermes/gateway_state.json"
        state = json.loads(path.read_text())
        state["platforms"]["api_server"] = {"state": "failed", "writer_pid": 1}
        path.write_text(json.dumps(state))
        status = self.run_manager("status", "hermes")
        self.assertEqual(status.returncode, 69, status.stdout + status.stderr)
        self.assertIn("Telegram connected", status.stdout)
        self.assertIsNone(gateway.poll())

    def test_hermes_startup_grace_does_not_restart(self):
        gateway = self.ready_hermes(gateway_state="starting")
        status = self.run_manager("recover", "hermes")
        self.assertEqual(status.returncode, 75, status.stdout + status.stderr)
        self.assertIn("STARTING", status.stdout)
        self.assertIsNone(gateway.poll())

    def test_hermes_intentional_cron_only_is_valid_without_telegram(self):
        self.ready_hermes(platforms={})
        self.hermes_config({})
        env = self.environment(2)
        env["HERMES_GATEWAY_MODE"] = "cron-only"
        status = subprocess.run([str(MANAGER), "status", "hermes"], env=env,
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertIn("RUNNING (cron-only)", status.stdout)

    def test_hermes_disabled_main_provider_is_blocked(self):
        gateway = self.ready_hermes()
        path = self.home / ".hermes/config.yaml"
        config = json.loads(path.read_text())
        config["providers"] = {"openai-codex": {"enabled": False}}
        path.write_text(json.dumps(config))
        result = self.run_manager("recover", "hermes")
        self.assertEqual(result.returncode, 78, result.stdout + result.stderr)
        self.assertIsNone(gateway.poll())

    def test_hermes_pid_only_is_unknown_not_recovered(self):
        self.start_gateway_stand_in()
        self.hermes_config()
        result = self.run_manager("status", "hermes")
        self.assertEqual(result.returncode, 69, result.stdout + result.stderr)
        self.assertIn("UNKNOWN", result.stdout)

    def test_hermes_profile_does_not_borrow_default_generation(self):
        gateway = self.ready_hermes()
        isolated = self.home / ".hermes/profiles/fixture"
        isolated.mkdir(parents=True)
        (isolated / "config.yaml").write_bytes((self.home / ".hermes/config.yaml").read_bytes())
        env = self.environment(2)
        env["HERMES_HOME"] = str(isolated)
        result = subprocess.run([str(MANAGER), "status", "hermes"], env=env,
                                text=True, capture_output=True, timeout=5)
        self.assertIn("STOPPED", result.stdout)
        self.assertIsNone(gateway.poll())

    def test_hermes_restart_does_not_leak_recovery_lock_to_replacement(self):
        self.ready_hermes()
        self.hermes_config({})
        original_environment = self.environment
        self.environment = lambda timeout: dict(original_environment(timeout), HERMES_GATEWAY_MODE="cron-only")
        self.write_executable("systemctl", "#!/bin/sh\nexit 1\n")
        self.write_executable("hermes", "#!/usr/bin/env python3\n"
            "import json, os, pathlib, signal, time\n"
            "home = pathlib.Path(os.environ['HOME']) / '.hermes'\n"
            "pid = os.getpid()\n"
            "ticks = pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]\n"
            "record = dict(kind='hermes-gateway', pid=pid, start_time=ticks, gateway_state='running', active_agents=0, "
            "platforms={'telegram': dict(state='connected', writer_pid=pid, writer_start_time=ticks)})\n"
            "(home / 'gateway_state.json').write_text(json.dumps(record))\n"
            "signal.signal(signal.SIGTERM, lambda *_: exit(0))\n"
            "time.sleep(30)\n")
        def cleanup():
            record = json.loads((self.home / ".hermes/gateway_state.json").read_text())
            pid = record["pid"]
            try:
                if pid > 1 and self.read_start_ticks(pid) == str(record["start_time"]):
                    os.kill(pid, signal.SIGTERM)
            except (FileNotFoundError, ProcessLookupError):
                pass
        self.fixture_gateway_cleanup = cleanup
        restarted = self.run_manager("restart", "hermes", timeout=3)
        self.assertEqual(restarted.returncode, 0, restarted.stdout + restarted.stderr)
        recovered = self.run_manager("recover", "hermes", timeout=3)
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)

    def test_hermes_restart_rejects_changed_expected_generation(self):
        gateway = self.ready_hermes()
        result = self.run_manager("restart", "hermes", f"{gateway.pid}:1")
        self.assertEqual(result.returncode, 75, result.stdout + result.stderr)
        self.assertIsNone(gateway.poll())

    def test_hermes_explicit_restart_preserves_active_work(self):
        gateway = self.ready_hermes(active_agents=1)
        self.hermes_config({})
        original_environment = self.environment
        self.environment = lambda timeout: dict(original_environment(timeout), HERMES_GATEWAY_MODE="cron-only")
        result = self.run_manager("restart", "hermes")
        self.assertEqual(result.returncode, 75, result.stdout + result.stderr)
        self.assertIsNone(gateway.poll())

    def start_process_named_hermes(self) -> subprocess.Popen[bytes]:
        impostor = self.bin / "hermes"
        impostor.write_bytes(Path("/bin/sleep").read_bytes())
        impostor.chmod(0o755)
        # Own isolated session: an impostor hermes must never share the test
        # runner's group, or a group signal could reach the coordinator.
        process = subprocess.Popen([str(impostor), "60"], start_new_session=True)
        self.register_owned(process)
        return process

    def hermes_status_line(self) -> str:
        result = self.run_manager("status", timeout=20)
        return next(line for line in result.stdout.splitlines() if "hermes gateway run" in line)

    def test_hermes_status_trusts_the_gateway_pid_record(self) -> None:
        self.ready_hermes()
        self.assertIn("Telegram connected; reply credential usability NOT-VERIFIED", self.hermes_status_line())

    def test_hermes_status_accepts_native_gateway_state_record(self) -> None:
        self.ready_hermes()
        self.assertIn("Telegram connected; reply credential usability NOT-VERIFIED", self.hermes_status_line())

    def test_hermes_stop_uses_native_gateway_state_record(self) -> None:
        gateway = self.start_gateway_stand_in()
        home = self.home / ".hermes"
        (home / "gateway.pid").rename(home / "gateway_state.json")
        stopped = self.run_manager("stop", "hermes", timeout=20)
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        gateway.wait(timeout=5)

    def test_hermes_status_rejects_wrong_record_kind(self) -> None:
        self.start_gateway_stand_in()
        path = self.home / ".hermes/gateway.pid"
        record = json.loads(path.read_text())
        record["kind"] = "not-a-gateway"
        path.write_text(json.dumps(record))
        self.assertEqual(self.hermes_status_line().strip(), "hermes gateway run: STOPPED")

    def test_hermes_status_rejects_a_recycled_pid(self) -> None:
        self.start_gateway_stand_in(ticks="1")
        self.assertEqual(self.hermes_status_line().strip(), "hermes gateway run: STOPPED")

    def test_hermes_status_ignores_other_processes_named_hermes(self) -> None:
        self.start_process_named_hermes()
        self.assertEqual(self.hermes_status_line().strip(), "hermes gateway run: STOPPED")

    def test_hermes_stop_signals_only_the_recorded_gateway(self) -> None:
        gateway = self.start_gateway_stand_in()
        session = self.start_process_named_hermes()
        stopped = self.run_manager("stop", "hermes", timeout=20)
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        gateway.wait(timeout=5)
        self.assertIsNone(session.poll(), "an interactive hermes process must survive a gateway stop")

    def test_nanobot_wrapper_imports_only_allowlisted_env_keys(self) -> None:
        workspace = self.home / "HelmCortex/FORGE/brain/nanobot"
        venv_bin = workspace / ".venv/bin"
        venv_bin.mkdir(parents=True)
        config_dir = self.home / ".config/nanobot-telegram"
        config_dir.mkdir(parents=True)
        (config_dir / "config.json").write_text("{}\n", encoding="utf-8")
        expected = {
            "NANOBOT_RECALL_MCP_URL": "synthetic recall URL",
            "NANOBOT_TOOLS__SSRF_WHITELIST": json.dumps(["synthetic SSRF marker"]),
            "NANOBOT_GATEWAY__HOST": "synthetic host value",
            "NANOBOT_GATEWAY__PORT": str(len("synthetic port value")),
        }
        probe = venv_bin / "nanobot"
        probe.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os\n"
            "print(json.dumps({key: value for key, value in os.environ.items() "
            "if key.startswith('NANOBOT_') and key in "
            + repr([*expected, "NANOBOT_UNLISTED"]) + "}))\n",
            encoding="utf-8",
        )
        probe.chmod(0o755)
        (config_dir / "env").write_text(
            "".join(f"{key}={value}\n" for key, value in expected.items())
            + "NANOBOT_UNLISTED=synthetic unlisted value\n",
            encoding="utf-8",
        )
        wrapper = HERE.parents[3] / "bin/nanobot-telegram"
        result = subprocess.run(
            [str(wrapper), "--help"],
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home)},
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_managed_nanobot_template_holds_no_network_addresses(self) -> None:
        templates = HERE.parents[4] / ".bots/templates"
        def strict_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        def invalid_constant(value):
            raise ValueError("nonfinite JSON constant")
        config = json.loads(
            (templates / "nanobot-config.json").read_text(encoding="utf-8"),
            object_pairs_hook=strict_pairs, parse_constant=invalid_constant,
        )
        self.assertNotIn("ssrfWhitelist", config["tools"])
        self.assertNotIn("host", config["gateway"])
        self.assertNotIn("port", config["gateway"])
        self.assertEqual(config["tools"]["mcpServers"]["recall"]["url"],
                         "${NANOBOT_RECALL_MCP_URL}")
        env_lines = (templates / "nanobot-telegram.env").read_text(encoding="utf-8").splitlines()
        for key in ("NANOBOT_RECALL_MCP_URL", "NANOBOT_TOOLS__SSRF_WHITELIST",
                    "NANOBOT_GATEWAY__HOST", "NANOBOT_GATEWAY__PORT"):
            self.assertIn(f"# {key}=", env_lines)
            self.assertFalse(any(line.startswith(key + "=") for line in env_lines))

    def test_nanobot_refuses_unprovisioned_token(self) -> None:
        self.prepare_nanobot_wrapper()
        (self.home / ".config/nanobot-telegram/env").write_text(
            "# TELEGRAM_BOT_TOKEN=\n", encoding="utf-8"
        )
        result = self.run_manager("start", "nanobot", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("TELEGRAM_BOT_TOKEN is not provisioned", result.stderr)

    def test_nanobot_rejects_stale_readiness_from_an_earlier_launch(self) -> None:
        self.prepare_nanobot_wrapper(emit_ready=False, stale_ready=True)
        self.write_executable("sleep", "#!/bin/sh\nexit 0\n")
        result = self.run_manager("start", "nanobot", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("failed Telegram readiness", result.stderr)
        self.assertFalse((self.home / ".config/nanobot-telegram/running").exists())

    def test_nanobot_run_as_missing_user_refuses(self) -> None:
        self.prepare_nanobot_wrapper()
        run_as = self.home / ".config/nanobot-telegram/run-as"
        run_as.write_text("agent-does-not-exist-2999\n", encoding="utf-8")
        result = self.run_manager("start", "nanobot", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("nanobot run-as user is missing", result.stderr)

    def test_nanobot_run_as_self_runs_locally(self) -> None:
        import getpass
        self.prepare_nanobot_wrapper()
        run_as = self.home / ".config/nanobot-telegram/run-as"
        run_as.write_text(getpass.getuser() + "\n", encoding="utf-8")
        result = self.run_manager("status", "nanobot", timeout=2)
        self.assertIn("nanobot: STOPPED", result.stdout)
        self.assertNotIn("run-as user is missing", result.stderr)

    def test_sanitized_boot_binds_core_node_before_opencode_preflight(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|opencode\n", encoding="utf-8")
        marker = self.root / "resolved-node"
        self.write_executable(
            "opencode-telegram-patch-apply",
            f"#!/bin/sh\ncommand -v node > {str(marker)!r}\nexit 23\n",
            directory=self.forge_bin,
        )
        result = self.run_manager("start", "opencode", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(marker.read_text().strip(), str(self.core_bin / "node"))

    def prepare_deepseek_harness(self, allowed_chat_ids: list[int]) -> None:
        plugin = self.home / "HelmCortex/NEXUS/git/dsh-telegram"
        plugin.mkdir(parents=True)
        plugin.joinpath("package.json").write_text(json.dumps({"name": "dsh-telegram"}), encoding="utf-8")
        plugin.joinpath("package-lock.json").write_text("{}", encoding="utf-8")
        plugin.joinpath("cordis.patch.yml").write_text(
            "- insert:\n    - id: dsh-telegram\n      name: dsh-telegram\n",
            encoding="utf-8",
        )
        plugin.joinpath("dist").mkdir()
        plugin.joinpath("dist/index.js").write_text("", encoding="utf-8")
        workspace = self.home / ".local/share/deepseek-harness-telegram/workspace"
        workspace.joinpath(".pi").mkdir(parents=True)
        workspace.joinpath(".pi/telegram.json").write_text(
            json.dumps(
                {
                    "security": {"allowedChatIds": allowed_chat_ids},
                    "model": {
                        "provider": "neuralwatt",
                        "model": "deepseek-v4.1-flash-flex",
                    },
                }
            ),
            encoding="utf-8",
        )
        token = self.home / ".config/deepseek-harness-telegram/token"
        token.parent.mkdir(parents=True)
        token.write_text("fake-token\n", encoding="utf-8")
        token.chmod(0o600)
        key = self.home / ".config/helmcortex/opencode-go.key"
        key.parent.mkdir(parents=True)
        key.write_text("fake-key\n", encoding="utf-8")
        key.chmod(0o600)
        settings_text = "\n".join(
            [
                "llm-pi-ai:",
                "  providers:",
                "    neuralwatt:",
                "      displayName: NeuralWatt",
                "      apiKeyEnv: NEURALWATT_API_KEY",
                "      api: openai-completions",
                "      baseURL: https://api.neuralwatt.com/v1",
                "      models:",
                "        - id: deepseek-v4.1-flash-flex",
                "          contextWindow: 1048576",
                "          compat:",
                "            thinkingFormat: deepseek",
                "",
            ]
        )
        dsh_home = self.home / ".local/share/deepseek-harness-telegram/dsh-home"
        dsh_home.mkdir(parents=True)
        dsh_home.joinpath("settings.yaml").write_text(settings_text, encoding="utf-8")
        templates = self.agents / "templates"
        templates.mkdir()
        templates.joinpath("deepseek-harness-settings.yaml").write_text(settings_text, encoding="utf-8")
        profile_patch_text = "\n".join(
            [
                "- id: agent-default-model",
                "  config:",
                "    provider: neuralwatt",
                "    model: deepseek-v4.1-flash-flex",
                "",
                "- id: llm-deepseek",
                "  disabled: true",
                "",
                "- id: web-search-deepseek",
                "  disabled: true",
                "",
                "- id: tool-web",
                "  disabled: true",
                "",
            ]
        )
        templates.joinpath("deepseek-harness-cordis.patch.yml").write_text(
            profile_patch_text, encoding="utf-8"
        )
        profile_dir = dsh_home / "profiles/helmcortex-telegram"
        profile_dir.mkdir(parents=True)
        profile_dir.joinpath("cordis.patch.yml").write_text(profile_patch_text, encoding="utf-8")
        env_file = self.home / ".config/deepseek-harness-telegram/env"
        env_file.write_text(
            "\n".join(
                [
                    f"TELEGRAM_BOT_TOKEN_FILE={token}",
                    f"NEURALWATT_API_KEY_FILE={key}",
                    f"DSH_HOME={self.home / '.local/share/deepseek-harness-telegram/dsh-home'}",
                    "DSH_TELEGRAM_PROFILE=helmcortex-telegram",
                    f"DSH_TELEGRAM_WORKSPACE={workspace}",
                    f"DSH_TELEGRAM_PLUGIN_ROOT={plugin}",
                    "DSH_TELEGRAM_MODEL_PROVIDER=neuralwatt",
                    "DSH_TELEGRAM_MODEL=deepseek-v4.1-flash-flex",
                    "DSH_TELEGRAM_PROVIDER_BASE_URL=https://api.neuralwatt.com/v1",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        env_file.chmod(0o600)
        self.write_executable(
            "dsh",
            "#!/bin/sh\n"
            "if [ \"$1\" = plugin ] && [ \"$2\" = --profile ] && [ \"$4\" = list ]; then\n"
            f"  printf '%s\\n' 'link:{plugin}'\n"
            "  exit 0\n"
            "fi\n"
            "trap 'exit 0' TERM INT\n"
            "while :; do sleep 1; done\n",
        )

    def test_deepseek_harness_refuses_missing_private_env(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        result = self.run_manager("start", "deepseek-harness", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("private env file is missing", result.stderr)

    def test_deepseek_harness_sync_refreshes_only_managed_profile_patch(self) -> None:
        self.prepare_deepseek_harness([123])
        template = self.agents / "templates/deepseek-harness-cordis.patch.yml"
        template.write_text(template.read_text(encoding="utf-8") + "# refreshed\n", encoding="utf-8")

        result = self.run_manager("sync", "deepseek-harness", timeout=2)

        self.assertEqual(result.returncode, 0, result.stderr)
        profile = (
            self.home
            / ".local/share/deepseek-harness-telegram/dsh-home/profiles/helmcortex-telegram/cordis.patch.yml"
        )
        self.assertEqual(profile.read_text(encoding="utf-8"), template.read_text(encoding="utf-8"))
        self.assertEqual(profile.stat().st_mode & 0o777, 0o600)

    def test_deepseek_harness_refuses_empty_allowlist(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        self.prepare_deepseek_harness([])
        result = self.run_manager("start", "deepseek-harness", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("allowedChatIds is empty", result.stderr)

    def test_deepseek_harness_rejects_inline_telegram_token(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        self.prepare_deepseek_harness([123])
        env_file = self.home / ".config/deepseek-harness-telegram/env"
        lines = [
            line for line in env_file.read_text(encoding="utf-8").splitlines()
            if not line.startswith("TELEGRAM_BOT_TOKEN_FILE=")
        ]
        lines.insert(0, "TELEGRAM_BOT_TOKEN=fake-inline-token")
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = self.run_manager("start", "deepseek-harness", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Telegram token file is missing", result.stderr)

    def test_deepseek_harness_status_rejects_pid_only_health(self) -> None:
        self.prepare_deepseek_harness([123])
        proc = subprocess.Popen(
            [str(self.bin / "dsh"), "--profile", "helmcortex-telegram"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=self.environment(2),
        )
        try:
            state_dir = self.state / "telegram-agents"
            state_dir.mkdir(parents=True)
            state_dir.joinpath("deepseek-harness.pid").write_text(str(proc.pid), encoding="utf-8")
            result = self.run_manager("status", "deepseek-harness", timeout=2)
            self.assertEqual(result.returncode, 1)
            self.assertIn("readiness owner state not verified", result.stdout)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_deepseek_harness_status_rejects_stale_marker(self) -> None:
        self.prepare_deepseek_harness([123])
        proc = subprocess.Popen(
            [str(self.bin / "dsh"), "--profile", "helmcortex-telegram"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=self.environment(2),
        )
        try:
            state_dir = self.state / "telegram-agents"
            state_dir.mkdir(parents=True)
            state_dir.joinpath("deepseek-harness.pid").write_text(str(proc.pid), encoding="utf-8")
            self.write_dsh_marker(proc.pid, start_ticks="0")
            result = self.run_manager("status", "deepseek-harness", timeout=2)
            self.assertEqual(result.returncode, 1)
            self.assertIn("readiness owner state not verified", result.stdout)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_deepseek_harness_status_rejects_wrong_launch_generation(self) -> None:
        self.prepare_deepseek_harness([123])
        proc = subprocess.Popen(
            [str(self.bin / "dsh"), "--profile", "helmcortex-telegram"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=self.environment(2),
        )
        try:
            state_dir = self.state / "telegram-agents"
            state_dir.mkdir(parents=True)
            state_dir.joinpath("deepseek-harness.pid").write_text(str(proc.pid), encoding="utf-8")
            self.write_dsh_marker(
                proc.pid,
                generation="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                expected_generation="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            )
            result = self.run_manager("status", "deepseek-harness", timeout=2)
            self.assertEqual(result.returncode, 1)
            self.assertIn("readiness owner state not verified", result.stdout)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_deepseek_harness_status_rejects_wrong_profile(self) -> None:
        self.prepare_deepseek_harness([123])
        proc = subprocess.Popen(
            [str(self.bin / "dsh"), "--profile", "helmcortex-telegram"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=self.environment(2),
        )
        try:
            state_dir = self.state / "telegram-agents"
            state_dir.mkdir(parents=True)
            state_dir.joinpath("deepseek-harness.pid").write_text(str(proc.pid), encoding="utf-8")
            self.write_dsh_marker(proc.pid, profile="other-profile")
            result = self.run_manager("status", "deepseek-harness", timeout=2)
            self.assertEqual(result.returncode, 1)
            self.assertIn("readiness owner state not verified", result.stdout)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_deepseek_harness_status_rejects_child_that_exited_after_marker(self) -> None:
        self.prepare_deepseek_harness([123])
        generation = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        state_dir = self.state / "telegram-agents"
        state_dir.mkdir(parents=True)
        state_dir.joinpath("deepseek-harness.generation").write_text(generation, encoding="utf-8")
        marker = state_dir / f"deepseek-harness.ready.{generation}"
        self.write_executable(
            "dsh",
            "#!/bin/sh\n"
            "pid=$$\n"
            "ticks=$(python3 -c 'from pathlib import Path; import sys; s=Path(f\"/proc/{sys.argv[1]}/stat\").read_text(); print(s[s.rfind(\")\") + 2:].split()[19])' \"$pid\")\n"
            "python3 - \"$DSH_TELEGRAM_READY_MARKER\" \"$pid\" \"$ticks\" <<'PY'\n"
            "import json, sys\n"
            "from pathlib import Path\n"
            "Path(sys.argv[1]).write_text(json.dumps({'schema': 1, 'component': 'dsh-telegram', 'pid': int(sys.argv[2]), 'start_ticks': sys.argv[3], 'profile': 'helmcortex-telegram', 'provider': 'neuralwatt', 'model': 'deepseek-v4.1-flash-flex', 'telegram_bot_identity_validated': True, 'long_polling_owned': True}), encoding='utf-8')\n"
            "PY\n"
            "exit 0\n",
        )
        proc = subprocess.Popen(
            [str(self.bin / "dsh"), "--profile", "helmcortex-telegram"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**self.environment(2), "DSH_TELEGRAM_READY_MARKER": str(marker)},
        )
        proc.wait(timeout=5)
        state_dir.joinpath("deepseek-harness.pid").write_text(str(proc.pid), encoding="utf-8")
        result = self.run_manager("status", "deepseek-harness", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("readiness owner state not verified", result.stdout)

    def test_deepseek_harness_start_refuses_markerless_lookalike_process(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        self.prepare_deepseek_harness([123])
        (self.home / ".local/share/deepseek-harness-telegram/dsh-home/profiles/helmcortex-telegram/package.json").write_text(
            json.dumps({"dependencies": {"dsh-telegram": f"link:{self.home / 'HelmCortex/NEXUS/git/dsh-telegram'}"}}), encoding="utf-8"
        )
        proc = subprocess.Popen(
            [str(self.bin / "dsh"), "--profile", "helmcortex-telegram"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=self.environment(2),
        )
        try:
            result = self.run_manager("start", "deepseek-harness", timeout=2)
            self.assertEqual(result.returncode, 1)
            self.assertIn("another dsh poller already uses profile", result.stderr)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_deepseek_harness_second_starter_refuses_while_first_holds_lock(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        self.prepare_deepseek_harness([123])
        lock_path = self.state / "telegram-agents/deepseek-harness.start.lock"
        holder = subprocess.Popen(
            [
                "python3",
                "-c",
                "import fcntl, pathlib, sys, time; p = pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True); f = p.open('w'); fcntl.flock(f, fcntl.LOCK_EX); time.sleep(5)",
                str(lock_path),
            ],
        )
        try:
            time.sleep(0.2)
            result = self.run_manager("start", "deepseek-harness", timeout=2)
            self.assertEqual(result.returncode, 1)
            self.assertIn("another DeepSeek Harness starter holds the launch lock", result.stderr)
        finally:
            holder.terminate()
            holder.wait(timeout=5)

    def test_deepseek_harness_status_accepts_matching_marker(self) -> None:
        self.prepare_deepseek_harness([123])
        proc = subprocess.Popen(
            [str(self.bin / "dsh"), "--profile", "helmcortex-telegram"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=self.environment(2),
        )
        try:
            state_dir = self.state / "telegram-agents"
            state_dir.mkdir(parents=True)
            state_dir.joinpath("deepseek-harness.pid").write_text(str(proc.pid), encoding="utf-8")
            self.write_dsh_marker(proc.pid)
            result = self.run_manager("status", "deepseek-harness", timeout=2)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("deepseek-harness: RUNNING", result.stdout)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_deepseek_harness_stop_migrates_verified_legacy_pid_only_owner(self) -> None:
        self.prepare_deepseek_harness([123])
        proc = subprocess.Popen(
            [str(self.bin / "dsh"), "--profile", "helmcortex-telegram"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=self.environment(2),
        )
        state_dir = self.state / "telegram-agents"
        state_dir.mkdir(parents=True)
        state_dir.joinpath("deepseek-harness.pid").write_text(str(proc.pid), encoding="utf-8")
        result = self.run_manager("stop", "deepseek-harness", timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        proc.wait(timeout=5)
        self.assertFalse(state_dir.joinpath("deepseek-harness.pid").exists())

    def test_deepseek_harness_stop_clears_stale_state_without_a_matching_process(self) -> None:
        self.prepare_deepseek_harness([123])
        state_dir = self.state / "telegram-agents"
        state_dir.mkdir(parents=True)
        state_dir.joinpath("deepseek-harness.pid").write_text("99999999", encoding="utf-8")
        state_dir.joinpath("deepseek-harness.ready").write_text("{}", encoding="utf-8")
        env = self.environment(2)
        env["DSH_TELEGRAM_PROFILE"] = "stale-test-profile"
        result = subprocess.run(
            [str(MANAGER), "stop", "deepseek-harness"],
            text=True,
            capture_output=True,
            env=env,
            timeout=7,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(state_dir.joinpath("deepseek-harness.pid").exists())
        self.assertFalse(state_dir.joinpath("deepseek-harness.ready").exists())

    def test_deepseek_harness_start_retires_dead_owner_before_model_preflight(self) -> None:
        manager_text = MANAGER.read_text(encoding="utf-8")
        start = manager_text.index("        deepseek-harness)\n")
        clear_marker = manager_text.index(
            "deepseek_harness_clear_stale_marker ||", start
        )
        retire_owner = manager_text.index(
            "deepseek_harness_retire_stale_owner ||", clear_marker
        )
        model_preflight = manager_text.index(
            "deepseek_harness_preflight_model ||", retire_owner
        )
        self.assertLess(clear_marker, retire_owner)
        self.assertLess(retire_owner, model_preflight)
        retire_function = manager_text[
            manager_text.index("deepseek_harness_retire_stale_owner()"):
            manager_text.index("deepseek_harness_kill_owned()")
        ]
        self.assertIn("deepseek_harness_find_unowned", retire_function)
        self.assertIn("refusing cleanup", retire_function)
        self.assertIn('rm -f "$DSH_TELEGRAM_PID_FILE"', retire_function)

    def test_deepseek_harness_rejects_model_fallback_in_private_config(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        self.prepare_deepseek_harness([123])
        config = self.home / ".local/share/deepseek-harness-telegram/workspace/.pi/telegram.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        data["model"] = {"provider": "neuralwatt", "model": "deepseek-v4-flash"}
        config.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_manager("start", "deepseek-harness", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no fallback is permitted", result.stderr)

    def test_deepseek_harness_rejects_native_deepseek_credential_route(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        self.prepare_deepseek_harness([123])
        profile_patch = (
            self.home
            / ".local/share/deepseek-harness-telegram/dsh-home/profiles/helmcortex-telegram/cordis.patch.yml"
        )
        profile_patch.write_text(
            "- id: agent-default-model\n"
            "  config:\n"
            "    provider: neuralwatt\n"
            "    model: deepseek-v4.1-flash-flex\n",
            encoding="utf-8",
        )
        result = self.run_manager("start", "deepseek-harness", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("refusing credential egress", result.stderr)

    def test_deepseek_harness_scrubs_ambient_deepseek_credentials(self) -> None:
        manager_text = MANAGER.read_text(encoding="utf-8")
        provider_scrub = "-u DEEPSEEK_API_KEY -u DEEPSEEK_API_KEY_FILE -u NEURALWATT_API_KEY -u OPENCODE_API_KEY -u OPENCODE_GO_API_KEY"
        self.assertGreaterEqual(manager_text.count(provider_scrub), 2)
        self.assertIn("env -u TELEGRAM_BOT_TOKEN " + provider_scrub, manager_text)
        self.assertNotIn('DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY"', manager_text)
        self.assertNotIn('NEURALWATT_API_KEY="$NEURALWATT_API_KEY"', manager_text)
        self.assertNotIn('OPENCODE_GO_API_KEY="$OPENCODE_GO_API_KEY"', manager_text)
        self.assertNotIn('TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN"', manager_text)

    def test_deepseek_harness_pins_neuralwatt_flex_defaults(self) -> None:
        manager_text = MANAGER.read_text(encoding="utf-8")
        self.assertIn('DSH_TELEGRAM_MODEL_PROVIDER:-neuralwatt', manager_text)
        self.assertIn('DSH_TELEGRAM_MODEL:-deepseek-v4.1-flash-flex', manager_text)
        self.assertIn('DSH_TELEGRAM_PROVIDER_BASE_URL:-https://api.neuralwatt.com/v1', manager_text)
        self.assertIn('neuralwatt/deepseek-v4.1-flash-flex/https://api.neuralwatt.com/v1', manager_text)
        self.assertIn('helmcortex-opencode-go/deepseek-v4.1-flash/https://opencode.ai/zen/go/v1', manager_text)
        self.assertIn('IFS= read -r NEURALWATT_API_KEY < "$NEURALWATT_API_KEY_FILE"', manager_text)
        self.assertIn('export NEURALWATT_API_KEY', manager_text)

    def test_deepseek_harness_manual_go_route_and_cross_route_refusal(self) -> None:
        manager_text = MANAGER.read_text(encoding="utf-8")
        route = manager_text.split("deepseek_harness_validate_route() {", 1)[1].split("\n}\n", 1)[0]
        function = "deepseek_harness_validate_route() {" + route + "\n}\n"
        routes = [
            ("neuralwatt", "deepseek-v4.1-flash-flex", "https://api.neuralwatt.com/v1", 0),
            ("helmcortex-opencode-go", "deepseek-v4.1-flash", "https://opencode.ai/zen/go/v1", 0),
            ("neuralwatt", "deepseek-v4.1-flash", "https://api.neuralwatt.com/v1", 1),
            ("helmcortex-opencode-go", "deepseek-v4.1-flash-flex", "https://opencode.ai/zen/go/v1", 1),
            ("neuralwatt", "deepseek-v4.1-flash-flex", "https://opencode.ai/zen/go/v1", 1),
            ("helmcortex-opencode-go", "deepseek-v4.1-flash", "https://api.neuralwatt.com/v1", 1),
            ("deepseek", "deepseek-v4.1-flash", "https://opencode.ai/zen/go/v1", 1),
        ]
        for provider, model, url, expected in routes:
            with self.subTest(provider=provider, model=model, url=url):
                result = subprocess.run(["bash", "-c", function + 'DSH_TELEGRAM_MODEL_PROVIDER="$1"; DSH_TELEGRAM_MODEL="$2"; DSH_TELEGRAM_PROVIDER_BASE_URL="$3"; deepseek_harness_validate_route', "test", provider, model, url], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
        self.assertIn('IFS= read -r OPENCODE_GO_API_KEY < "$OPENCODE_GO_API_KEY_FILE"', manager_text)
        self.assertIn('export OPENCODE_GO_API_KEY', manager_text)

    def test_deepseek_harness_catalogs_retain_manual_go_and_flex_default(self) -> None:
        templates = MANAGER.parents[2] / ".bots/templates"
        settings = (templates / "deepseek-harness-settings.yaml").read_text()
        patch = (templates / "deepseek-harness-cordis.patch.yml").read_text()
        for catalog in (settings, patch):
            neural, go = catalog.split("    helmcortex-opencode-go:", 1)
            self.assertIn("apiKeyEnv: NEURALWATT_API_KEY", neural)
            self.assertNotIn("x-opencode-session", neural)
            self.assertIn("apiKeyEnv: OPENCODE_GO_API_KEY", go)
            self.assertIn("x-opencode-session: helmcortex-deepseek-harness", go)
        self.assertIn("    provider: neuralwatt\n    model: deepseek-v4.1-flash-flex", patch)
        config = json.loads((templates / "deepseek-harness-telegram.json").read_text())
        self.assertEqual(config["model"], {"provider": "neuralwatt", "model": "deepseek-v4.1-flash-flex"})
        env = (templates / "deepseek-harness-telegram.env").read_text()
        self.assertIn("DSH_TELEGRAM_MODEL_PROVIDER=neuralwatt", env)
        self.assertIn("OPENCODE_GO_API_KEY_FILE=YOUR_HELMCORTEX_OPENCODE_GO_KEY_FILE", env)

    def durability_python(self, function: str) -> str:
        text = MANAGER.read_text().split(function + "() {", 1)[1]
        return text.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]

    def test_deepseek_harness_durability_native_credentials(self) -> None:
        import sys
        home = self.root.resolve() / "synthetic-dsh-home"
        home.mkdir(mode=0o700)
        store = home / ".credentials.yaml"
        synthetic = "SYNTHETIC-FIXTURE-NOT-A-REAL-KEY"
        baseline = "refs:\n  NEURALWATT_API_KEY: " + synthetic + "\n  OTHER_REF: SYNTHETIC-OTHER\n"
        store.write_text(baseline)
        store.chmod(0o600)
        code = self.durability_python("deepseek_harness_provider_check")
        env = dict(os.environ, DSH_HOME=str(home), DSH_TELEGRAM_MODEL_PROVIDER="neuralwatt",
                   DSH_TELEGRAM_MODEL="deepseek-v4.1-flash-flex",
                   DSH_TELEGRAM_PROVIDER_BASE_URL="https://api.neuralwatt.com/v1",
                   NEURALWATT_API_KEY_FILE="")
        # Real preflight code, mocked transport only; no network or live provider.
        mock = ("import io,sys,urllib.request\n"
                "def mocked(request, **kwargs):\n"
                "    assert request.get_header('Authorization') == 'Bearer SYNTHETIC-FIXTURE-NOT-A-REAL-KEY'\n"
                "    return io.StringIO('{\"data\":[{\"id\":\"deepseek-v4.1-flash-flex\"}]}')\n"
                "urllib.request.urlopen = mocked\n")
        def run(expected: int, prefix: str = "", mode: str = "validate") -> None:
            result = subprocess.run([sys.executable, "-c", prefix + code, mode], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertNotIn(synthetic, result.stdout + result.stderr)
            self.assertNotIn("SYNTHETIC-OTHER", result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        run(0)
        run(0, mock, "preflight")
        self.assertEqual(store.read_text(), baseline)
        store.chmod(0o640)
        run(1)
        store.chmod(0o600)
        run(1, "import os\nos.geteuid = lambda: -1\n")
        wrong_file_owner = ("import os\n_real_fstat = os.fstat\n"
                            "def wrong_owner(fd):\n"
                            "    fields = list(_real_fstat(fd)); fields[4] = -1\n"
                            "    return os.stat_result(fields)\n"
                            "os.fstat = wrong_owner\n")
        run(1, wrong_file_owner)
        store.write_text("refs: {}\n")
        run(1)
        store.write_text("refs: [malformed: [\n" + synthetic)
        run(1)
        store.write_text(baseline)
        other = home / "synthetic-store"
        store.rename(other)
        store.symlink_to(other)
        run(1)
        store.unlink()
        other.rename(store)
        key = self.root / "synthetic-key-file"
        key.write_text(synthetic + "\n")
        key.chmod(0o600)
        env["NEURALWATT_API_KEY_FILE"] = str(key)
        run(0)
        run(0, mock, "preflight")
        run(1, wrong_file_owner)
        key.chmod(0o644)
        run(1)  # Do not hide an invalid explicit file behind a valid native ref.
        key.unlink()
        run(1)
        env["NEURALWATT_API_KEY_FILE"] = ""
        store.unlink()
        run(1)

    def test_deepseek_harness_durability_settings_semantics(self) -> None:
        import copy
        import sys
        import yaml
        template = MANAGER.parents[2] / ".bots/templates/deepseek-harness-settings.yaml"
        approved = yaml.safe_load(template.read_text())
        actual = self.root / "synthetic-settings.yaml"
        code = self.durability_python("deepseek_harness_validate_private_config")
        def run(data: dict, expected: int) -> None:
            actual.write_text(yaml.safe_dump(data, sort_keys=True))
            result = subprocess.run([sys.executable, "-c", code, str(actual), str(template)], text=True, capture_output=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertNotIn("SYNTHETIC-INLINE-SECRET", result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        run(approved, 0)
        for provider, model in [("neuralwatt", "deepseek-v4.1-flash-flex"), ("helmcortex-opencode-go", "deepseek-v4.1-flash")]:
            data = copy.deepcopy(approved)
            data["agent-default-model"] = {"provider": provider, "model": model}
            run(data, 0)
        for field, value in [("baseURL", "https://unapproved.invalid"), ("apiKeyEnv", "OTHER_KEY"),
                             ("apiKey", "SYNTHETIC-INLINE-SECRET"), ("headers", {"Authorization": "SYNTHETIC-INLINE-SECRET"}),
                             ("models", [{"id": "unapproved"}])]:
            data = copy.deepcopy(approved)
            data["llm-pi-ai"]["providers"]["neuralwatt"][field] = value
            run(data, 1)
        data = copy.deepcopy(approved)
        data["llm-pi-ai"]["providers"]["foreign"] = {}
        run(data, 1)
        data = copy.deepcopy(approved)
        data["foreign-setting"] = {}
        run(data, 1)
        for selection in [None, {"provider": "neuralwatt", "model": "deepseek-v4.1-flash"},
                          {"provider": "neuralwatt", "model": "deepseek-v4.1-flash-flex", "apiKey": "SYNTHETIC-INLINE-SECRET"}]:
            data = copy.deepcopy(approved)
            data["agent-default-model"] = selection
            run(data, 1)

    def test_deepseek_harness_log_redactor_lives_in_detached_session(self) -> None:
        manager_text = MANAGER.read_text(encoding="utf-8")
        detached = manager_text.index('exec nohup setsid env -u TELEGRAM_BOT_TOKEN')
        detached_shell = manager_text.index("bash -c '", detached)
        redactor = manager_text.index("sed -u -E", detached_shell)
        launch = manager_text.index('exec dsh --profile "$DSH_TELEGRAM_PROFILE"', detached_shell)
        pid_publish = manager_text.index('printf \'%s\\n\' "$launched_pid" > "$DSH_TELEGRAM_PID_FILE"', launch)
        self.assertLess(detached_shell, launch)
        self.assertLess(launch, redactor)
        self.assertLess(redactor, pid_publish)
        self.assertIn('NEURALWATT_API_KEY_FILE="$NEURALWATT_API_KEY_FILE"', manager_text)

    def test_deepseek_harness_readiness_marker_contract_excludes_secrets_and_ids(self) -> None:
        manager_text = MANAGER.read_text(encoding="utf-8")
        self.assertIn('DSH_TELEGRAM_READY_MARKER=', manager_text)
        self.assertIn('DSH_TELEGRAM_GENERATION_FILE=', manager_text)
        self.assertIn('launch_generation', manager_text)
        self.assertIn('launch_marker="${DSH_TELEGRAM_READY_MARKER}.${launch_generation}"', manager_text)
        self.assertIn('data.get("generation") != sys.argv[5]', manager_text)
        self.assertIn('DSH_TELEGRAM_READY_TIMEOUT="${DSH_TELEGRAM_READY_TIMEOUT:-120}"', manager_text)
        self.assertIn('telegram_bot_identity_validated', manager_text)
        self.assertIn('long_polling_owned', manager_text)
        self.assertNotIn('TELEGRAM_BOT_TOKEN', manager_text[manager_text.index('deepseek_harness_marker_matches'):manager_text.index('deepseek_harness_wait_ready')])
        self.assertNotIn('chatId', manager_text[manager_text.index('deepseek_harness_marker_matches'):manager_text.index('deepseek_harness_wait_ready')])

    def test_deepseek_harness_uses_canonical_recall_endpoint(self) -> None:
        profile = HERE.parents[3] / "../.bots/templates/deepseek-harness-cordis.patch.yml"
        profile_text = profile.resolve().read_text(encoding="utf-8")
        self.assertIn("url: @DSH_RECALL_MCP_URL@", profile_text)
        # Rule 21: the public template never carries a tailnet or private address.
        self.assertIsNone(re.search(r"\b(100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])|10\.[0-9]{1,3}|192\.168)\.[0-9]{1,3}\.[0-9]{1,3}\b", profile_text))

    def test_deepseek_harness_renders_recall_url_before_comparing(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        self.prepare_deepseek_harness([123])
        template = self.agents / "templates/deepseek-harness-cordis.patch.yml"
        template.write_text(template.read_text(encoding="utf-8") + "url: @DSH_RECALL_MCP_URL@\n", encoding="utf-8")
        profile_patch = (
            self.home
            / ".local/share/deepseek-harness-telegram/dsh-home/profiles/helmcortex-telegram/cordis.patch.yml"
        )
        rendered = template.read_text(encoding="utf-8").replace("@DSH_RECALL_MCP_URL@", "http://recall.invalid:3004/mcp")
        profile_patch.write_text(rendered, encoding="utf-8")
        env_file = self.home / ".config/deepseek-harness-telegram/env"
        env_file.write_text(env_file.read_text(encoding="utf-8") + "DSH_RECALL_MCP_URL=http://recall.invalid:3004/mcp\n", encoding="utf-8")
        result = self.run_manager("start", "deepseek-harness", timeout=2)
        self.assertNotIn("refusing credential egress", result.stderr)
        self.assertNotIn("cannot resolve the Recall MCP URL", result.stderr)
        # A profile that keeps the unrendered placeholder is refused.
        profile_patch.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        result = self.run_manager("start", "deepseek-harness", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("refusing credential egress", result.stderr)

    def prepare_deepseek_web_trust(self) -> tuple[Path, Path, str]:
        self.prepare_deepseek_harness([123])
        template = self.agents / "templates/deepseek-harness-cordis.patch.yml"
        canonical = HERE.parents[4] / ".bots/templates/deepseek-harness-cordis.patch.yml"
        template.write_text(canonical.read_text(encoding="utf-8"), encoding="utf-8")
        profile = self.home / ".local/share/deepseek-harness-telegram/dsh-home/profiles/helmcortex-telegram/cordis.patch.yml"
        env_file = self.home / ".config/deepseek-harness-telegram/env"
        env_text = env_file.read_text(encoding="utf-8") + "DSH_RECALL_MCP_URL=http://recall.invalid:3004/mcp\n"
        return profile, env_file, env_text

    def test_deepseek_harness_sync_renders_private_web_authority(self) -> None:
        profile, env_file, env_text = self.prepare_deepseek_web_trust()
        authority = ".".join(("browser", "example", "invalid")) + ":3080"
        env_file.write_text(env_text + f'export DSH_WEB_TRUSTED_HOST="{authority}"\n', encoding="utf-8")
        called = self.root / "tailscale-called"
        self.write_executable("tailscale", f"#!/bin/sh\ntouch {str(called)!r}\nexit 1\n")

        result = self.run_manager("sync", "deepseek-harness", timeout=2)

        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = profile.read_text(encoding="utf-8")
        self.assertIn(f"- id: connection\n  config:\n    trustedHosts: ['{authority}']", rendered)
        self.assertIn("url: http://recall.invalid:3004/mcp", rendered)
        self.assertNotIn("@DSH_", rendered)
        self.assertEqual(profile.stat().st_mode & 0o777, 0o600)
        self.assertFalse(called.exists(), "an explicit authority must bypass tailnet discovery")

    def test_deepseek_harness_sync_derives_web_authority_from_tailnet_suffix(self) -> None:
        profile, env_file, env_text = self.prepare_deepseek_web_trust()
        env_file.write_text(env_text + "DSH_WEB_TRUSTED_HOST=\n", encoding="utf-8")
        suffix = ".".join(("example", "invalid"))
        self.write_executable("hostname", "#!/bin/sh\n[ \"$1\" = -s ] || exit 1\nprintf '%s\\n' seat\n")
        for terminal_dot in ("", "."):
            with self.subTest(terminal_dot=terminal_dot):
                payload = json.dumps({"Self": {"DNSName": f"different-name.{suffix}{terminal_dot}"}})
                self.write_executable("tailscale", f"#!/bin/sh\n[ \"$1 $2\" = 'status --json' ] || exit 1\nprintf '%s\\n' '{payload}'\n")
                result = self.run_manager("sync", "deepseek-harness", timeout=2)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"trustedHosts: ['seat.{suffix}:3080']", profile.read_text(encoding="utf-8"))

    def test_deepseek_harness_sync_preserves_patch_when_web_trust_fails(self) -> None:
        profile, env_file, env_text = self.prepare_deepseek_web_trust()
        original = profile.read_bytes()
        authority = ".".join(("browser", "example", "invalid")) + ":3080"
        cases = (
            ("", "exit 1", "cannot resolve the web trusted host"),
            ("", "printf '%s' not-json", "cannot resolve the web trusted host"),
            ("", "printf '%s' '{}'", "cannot resolve the web trusted host"),
            ("", "printf '%s' '{\"Self\":{\"DNSName\":\"\"}}'", "cannot resolve the web trusted host"),
            (f"https://{authority}", "exit 1", "must be a bare DNS"),
            (f"{authority}/path", "exit 1", "must be a bare DNS"),
            (authority.replace(":3080", ":03080"), "exit 1", "must be a bare DNS"),
            (authority.replace(":3080", ":65536"), "exit 1", "must be a bare DNS"),
            (authority + "'injected", "exit 1", "must be a bare DNS"),
        )
        for value, status_body, message in cases:
            with self.subTest(value=value, status_body=status_body):
                env_file.write_text(env_text + f"DSH_WEB_TRUSTED_HOST={value}\n", encoding="utf-8")
                self.write_executable("tailscale", "#!/bin/sh\n" + status_body + "\n")
                result = self.run_manager("sync", "deepseek-harness", timeout=2)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(message, result.stderr)
                self.assertEqual(profile.read_bytes(), original)
                self.assertFalse(list(profile.parent.glob(".cordis.patch.yml.*")))

    def test_deepseek_harness_run_as_missing_user_refuses(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        run_as = self.home / ".config/deepseek-harness-telegram/run-as"
        run_as.parent.mkdir(parents=True, exist_ok=True)
        run_as.write_text("agent-does-not-exist-2999\n", encoding="utf-8")
        result = self.run_manager("start", "deepseek-harness", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("run-as user is missing", result.stderr)

    def test_deepseek_harness_run_as_self_runs_locally(self) -> None:
        import getpass
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        run_as = self.home / ".config/deepseek-harness-telegram/run-as"
        run_as.parent.mkdir(parents=True, exist_ok=True)
        run_as.write_text(getpass.getuser() + "\n", encoding="utf-8")
        result = self.run_manager("status", "deepseek-harness", timeout=2)
        self.assertIn("deepseek-harness:", result.stdout)
        self.assertNotIn("run-as user is missing", result.stderr)

    def test_codex_managed_start_clears_inherited_runtime_policy(self) -> None:
        source = MANAGER.read_text(encoding="utf-8")
        codex_start = source.split("        codex)\n", 1)[1].split(
            "        deepseek-harness)", 1
        )[0]
        for name in (
            "CODEX_HELMASTRA_MODEL",
            "CODEX_TELEGRAM_MODEL",
            "CODEX_HELMASTRA_EFFORT",
            "CODEX_TELEGRAM_EFFORT",
            "CODEX_TELEGRAM_APPROVAL_POLICY",
            "CODEX_TELEGRAM_APPROVALS_REVIEWER",
        ):
            self.assertIn(f"-u {name}", codex_start)

    # -- Shoukichi (vibe-bridge) -------------------------------------------

    def prepare_shoukichi(self) -> None:
        workspace = self.home / "HelmCortex/FORGE/brain/shoukichi"
        workspace.mkdir(parents=True)
        (workspace / "AGENTS.md").write_text(
            "# Shoukichi synthetic identity\n", encoding="utf-8"
        )
        venv_bin = self.home / "HelmCortex/NEXUS/git/vibe-bridge/.venv/bin"
        venv_bin.mkdir(parents=True)
        self.shoukichi_bridge_py = venv_bin / "python"
        # The manager verifies ownership against the EXACT argv
        # ".venv/bin/python -m vibe_bridge.main" read from /proc/cmdline,
        # so the fake must keep that argv itself — no exec -a disguise.
        self.write_looping_bridge(self.shoukichi_bridge_py)
        config_dir = self.home / ".config/vibe-telegram"
        config_dir.mkdir(parents=True)
        (config_dir / "vibe-home").mkdir()
        (config_dir / "vibe-home/config.toml").write_text(
            'default_agent = "ask"\nactive_model = "zai-glm-5-3"\n',
            encoding="utf-8",
        )
        (config_dir / "env").write_text(
            "TELEGRAM_BOT_TOKEN=123456789:abcdefghijklmnopqrstuvwxyzABCDE\n"
            "TELEGRAM_ALLOWED_USER_IDS=123456789\n"
            "MISTRAL_VIBE_API_KEY=synthetic-vibe-key\n",
            encoding="utf-8",
        )
        # The manager resolves the wrapper from DOTCORTEX_BIN_DIR's default,
        # $HOME/DotCortex/all/.local/bin — never the user's ~/.local/bin.
        dotcortex_bin = self.home / "DotCortex/all/.local/bin"
        dotcortex_bin.mkdir(parents=True)
        self.write_executable(
            "shoukichi-telegram",
            # The manager verifies ownership against the EXACT argv the real
            # wrapper produces: `$VENV_PY -m vibe_bridge.main`. The fake must
            # reproduce that argv so /proc/cmdline matches.
            "#!/bin/sh\nexec " + str(self.shoukichi_bridge_py) + " -m vibe_bridge.main\n",
            directory=dotcortex_bin,
        )

    def write_looping_bridge(self, bridge_py: Path) -> None:
        # Long-running, ignores TERM (stop must force the verified KILL
        # path), and — because it is a shell script, so `python -m X` runs
        # via the interpreter named in its shebang — it must not clobber
        # argv: bash keeps `-m vibe_bridge.main` as arguments and the
        # identity check reads them from /proc/cmdline unchanged.
        bridge_py.parent.mkdir(parents=True, exist_ok=True)
        bridge_py.write_text(
            "#!/bin/sh\n"
            "trap '' TERM INT\n"
            "while :; do sleep 1; done\n",
            encoding="utf-8",
        )
        bridge_py.chmod(0o755)

    def write_exit_zero_bridge(self, bridge_py: Path) -> None:
        bridge_py.parent.mkdir(parents=True, exist_ok=True)
        bridge_py.write_text(
            "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
        )
        bridge_py.chmod(0o755)

    def test_shoukichi_targeted_lifecycle_and_argv_ownership(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|shoukichi\n", encoding="utf-8")
        self.prepare_shoukichi()
        started = self.run_manager("start", "shoukichi", timeout=8)
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        status = self.run_manager("status", "shoukichi", timeout=4)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertRegex(status.stdout, r"^shoukichi: RUNNING pid=\d+ \(vibe-bridge\)\n$")
        stopped = self.run_manager("stop", "shoukichi", timeout=8)
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        pid_file = self.state / "vibe-telegram/adapter.pid"
        self.assertFalse(pid_file.exists())

    def test_shoukichi_start_refuses_missing_private_env(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|shoukichi\n", encoding="utf-8")
        self.prepare_shoukichi()
        (self.home / ".config/vibe-telegram/env").unlink()
        result = self.run_manager("start", "shoukichi", timeout=4)
        self.assertEqual(result.returncode, 1)
        self.assertIn("private env missing", result.stderr)

    def test_shoukichi_status_rejects_a_recycled_pid(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|shoukichi\n", encoding="utf-8")
        self.prepare_shoukichi()
        pid_file = self.state / "vibe-telegram/adapter.pid"
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        # A recycled PID is simulated with a value that is dead by construction
        # and never init: pid 1 in a fixture made tearDown's killpg(1) SIGTERM
        # the whole user session (the 2026-10-09 three-kill night). Use the
        # opencode fixture's certainly-dead convention instead, and keep the
        # manager's refusal assertion identical.
        pid_file.write_text("999999991\n", encoding="utf-8")
        status = self.run_manager("status", "shoukichi", timeout=4)
        self.assertIn("shoukichi: STOPPED", status.stdout)

    def test_shoukichi_status_refuses_pid_one_entirely(self) -> None:
        # Belt and braces: even if a future fixture drops a 1 here, the
        # manager must report stopped and nothing may signal it.
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|shoukichi\n", encoding="utf-8")
        self.prepare_shoukichi()
        pid_file = self.state / "vibe-telegram/adapter.pid"
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text("1\n", encoding="utf-8")
        status = self.run_manager("status", "shoukichi", timeout=4)
        self.assertIn("shoukichi: STOPPED", status.stdout)
        stopped = self.run_manager("stop", "shoukichi", timeout=4)
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        self.assertIn("not running", stopped.stdout)

    def test_shoukichi_stop_never_signals_an_unsafe_target(self) -> None:
        # RED test (Fable 2026-10-09, ask 2): if any stop path can ever
        # signal pid or group 0, 1, empty, or negative, this fails. Each
        # adversarial pid file must produce a clean refusal — "not running"
        # or the verified-kill guard message — and never reach a kill.
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|shoukichi\n", encoding="utf-8")
        self.prepare_shoukichi()
        pid_file = self.state / "vibe-telegram/adapter.pid"
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        for adversarial in ("0\n", "1\n", "\n", "-1\n", "not-a-pid\n"):
            pid_file.write_text(adversarial, encoding="utf-8")
            stopped = self.run_manager("stop", "shoukichi", timeout=4)
            self.assertEqual(stopped.returncode, 0, stopped.stderr)
            self.assertIn("not running", stopped.stdout)
            # Nothing was signalled: no guard message, no forced kill, and
            # the pid file is untouched by stop (removal is only for a
            # verified owner).
            self.assertNotIn("verified kill", stopped.stderr)
            self.assertNotIn("refusing unsafe PID target", stopped.stderr)

    def test_manager_and_teardown_kill_sites_are_guarded(self) -> None:
        # Static guard (Fable 2026-10-09 ask 2; hardened 2026-10-25): no kill
        # site may signal a GROUP from a pid read out of a file. tearDown must
        # never os.killpg a file-read pid (killpg's argument is a group id, so
        # a stale/recycled value SIGTERMs a bystander group). Group signalling
        # is allowed ONLY inside terminate_owned_group, after the owned-Popen
        # + kernel-start-ticks + isolated-group + not-ours validation. The
        # manager-side shoukichi verified-kill guard is preserved. If someone
        # reverts any guard, this fails at the source level.
        manager_text = (HERE.parents[3] / "bin/telegram-agent-host").read_text(encoding="utf-8")
        test_text = HERE.read_text(encoding="utf-8")
        # shoukichi_verified_kill refuses 0/1/non-numeric before any signal.
        self.assertIn("case \"$pid\" in ''|*[!0-9]*|0|1)", manager_text)
        # The group form is reachable ONLY through the helper's pgid==pid
        # branch; the shoukichi stop path must not contain its own kill.
        shoukichi_stop = manager_text.split("stop_shoukichi() {")[1].split("}\n\n")[0]
        self.assertNotIn("kill -", shoukichi_stop.replace("shoukichi_verified_kill", ""))
        # tearDown reaps pid-file children by single-pid, cmdline-validated
        # SIGTERM only -- never a group signal from a file. Assert on the
        # tearDown body, not the whole file: the file contains this guard's
        # own string literals, so a whole-file assertNotIn would match itself.
        teardown = test_text.split("    def tearDown(self) -> None:")[1].split("    def read_start_ticks")[0]
        self.assertNotIn("os.killpg(", teardown)
        self.assertNotIn("recorded_pid", teardown)
        self.assertIn("_cleanup_pid_file_child", teardown)
        # Group signalling lives only inside the ownership-validated helper,
        # and the ownership validation precedes every killpg.
        self.assertIn("def terminate_owned_group", test_text)
        self.assertIn("def _owns_isolated_group", test_text)
        helper = test_text.split("    def terminate_owned_group")[1].split("    def _cleanup_pid_file_child")[0]
        self.assertIn("_owns_isolated_group(proc, entry[1])", helper)
        self.assertLess(helper.index("_owns_isolated_group(proc, entry[1])"), helper.index("os.killpg"))

    @staticmethod
    def _legacy_pidfile_killpg(pid_value: int) -> None:
        # Pre-hardening tearDown primitive, kept only to characterise the bug:
        # read a pid from a file, refuse only pid <= 1, then killpg (a GROUP
        # signal whose argument is a pgid, not a pid).
        if pid_value <= 1:
            return
        os.killpg(pid_value, signal.SIGTERM)

    def test_legacy_pidfile_killpg_would_signal_a_bystander_group(self) -> None:
        # RED characterisation, mocked: no real signal is sent. A bystander
        # daemon in its own session is a group leader (pgid == pid), exactly
        # like the gateway. The legacy file-driven killpg SIGTERMs its group.
        bystander = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.addCleanup(lambda: (bystander.poll() is None and bystander.kill(), bystander.wait()))
        with mock.patch("os.killpg") as killpg:
            self._legacy_pidfile_killpg(bystander.pid)
        killpg.assert_called_once_with(bystander.pid, signal.SIGTERM)

    def test_terminate_owned_group_refuses_unsafe_targets(self) -> None:
        # GREEN, mocked: the hardened helper signals nothing for a bystander
        # group, a stale/recycled pid, a non-isolated (own-group) process, or
        # our own pid. No real signal is sent.
        bystander = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.addCleanup(lambda: (bystander.poll() is None and bystander.kill(), bystander.wait()))
        nonisolated = subprocess.Popen(["sleep", "60"])
        self.addCleanup(lambda: (nonisolated.poll() is None and nonisolated.kill(), nonisolated.wait()))
        owned = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.register_owned(owned)
        try:
            with mock.patch("os.killpg") as killpg, mock.patch("os.kill") as kill:
                # Unregistered bystander group: refused, nothing signalled.
                self.assertFalse(self.terminate_owned_group(bystander))
                killpg.assert_not_called()
                kill.assert_not_called()
                # Owned but stale/recycled start ticks: refused.
                self.assertFalse(self._owns_isolated_group(owned, "0"))
                killpg.assert_not_called()
                # Non-isolated child (shares our group): refused.
                self.assertFalse(self._owns_isolated_group(
                    nonisolated, self._proc_ticks(nonisolated.pid) or ""))
                killpg.assert_not_called()
                # Our own pid: refused.
                self.assertFalse(self._owns_isolated_group(
                    mock.Mock(pid=os.getpid()), self._proc_ticks(os.getpid()) or ""))
                killpg.assert_not_called()
        finally:
            for proc in (bystander, nonisolated, owned):
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()

    def test_terminate_owned_group_signals_only_the_owned_isolated_group(self) -> None:
        # GREEN (positive, real but safe): a registered, isolated, identity-
        # matching fixture group IS reaped, and a bystander group is not
        # touched. Only our own fixture sleep is ever signalled.
        owned = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.register_owned(owned)
        bystander = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.addCleanup(lambda: (bystander.poll() is None and bystander.kill(), bystander.wait()))
        try:
            self.assertTrue(self.terminate_owned_group(owned))
            self.assertIsNotNone(owned.poll(), "owned fixture group was not reaped")
            self.assertIsNone(bystander.poll(), "bystander group must survive owned cleanup")
        finally:
            for proc in (owned, bystander):
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()

    def test_shoukichi_wrapper_imports_only_allowlisted_env_keys(self) -> None:
        self.prepare_shoukichi()
        config_dir = self.home / ".config/vibe-telegram"
        (config_dir / "env").write_text(
            "TELEGRAM_BOT_TOKEN=123456789:abcdefghijklmnopqrstuvwxyzABCDE\n"
            "TELEGRAM_ALLOWED_USER_IDS=123456789\n"
            "MISTRAL_VIBE_API_KEY=synthetic-vibe-key\n"
            "MISTRAL_API_KEY=synthetic-studio-key\n"
            "TELEGRAM_ALLOWED_USER_IDS_EVIL=999\n",
            encoding="utf-8",
        )
        probe = self.home / "HelmCortex/NEXUS/git/vibe-bridge/.venv/bin/python"
        probe.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os\n"
            "print(json.dumps({key: value for key, value in os.environ.items() "
            "if key in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_USER_IDS', "
            "'MISTRAL_API_KEY', 'MISTRAL_VIBE_API_KEY', "
            "'VIBE_HOME', 'VIBE_BRIDGE_WORKSPACE', 'VIBE_BRIDGE_LANG', "
            "'ACP_AGENT_COMMAND', 'VIBE_BRIDGE_FORBIDDEN_MODES', "
            "'VIBE_BRIDGE_HTTP_TOKEN')}))\n",
            encoding="utf-8",
        )
        probe.chmod(0o755)
        wrapper = HERE.parents[3] / "bin/shoukichi-telegram"
        result = subprocess.run(
            [str(wrapper)],
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home)},
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed["TELEGRAM_BOT_TOKEN"], "123456789:abcdefghijklmnopqrstuvwxyzABCDE")
        self.assertEqual(observed["TELEGRAM_ALLOWED_USER_IDS"], "123456789")
        # The subscription key rides the provider env name; the Studio key
        # from the private file must NOT survive as MISTRAL_API_KEY.
        self.assertEqual(observed["MISTRAL_API_KEY"], "synthetic-vibe-key")
        self.assertNotIn("MISTRAL_VIBE_API_KEY", observed)
        self.assertEqual(observed["VIBE_BRIDGE_LANG"], "en")
        self.assertEqual(observed["ACP_AGENT_COMMAND"], "vibe-acp")
        self.assertEqual(observed["VIBE_BRIDGE_FORBIDDEN_MODES"], "auto-approve")
        # The HTTP automation endpoint stays disabled: no token is imported.
        self.assertNotIn("VIBE_BRIDGE_HTTP_TOKEN", observed)
        self.assertTrue(observed["VIBE_HOME"].endswith("/vibe-home"))
        self.assertTrue(observed["VIBE_BRIDGE_WORKSPACE"].endswith("/FORGE/brain/shoukichi"))

    def test_shoukichi_wrapper_refuses_each_missing_private_value(self) -> None:
        self.prepare_shoukichi()
        env_file = self.home / ".config/vibe-telegram/env"
        full = env_file.read_text(encoding="utf-8")
        wrapper = HERE.parents[3] / "bin/shoukichi-telegram"
        base_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home)}
        for missing, message in (
            ("TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN is not provisioned"),
            ("TELEGRAM_ALLOWED_USER_IDS", "TELEGRAM_ALLOWED_USER_IDS is not provisioned"),
            ("MISTRAL_VIBE_API_KEY", "MISTRAL_VIBE_API_KEY is not provisioned"),
        ):
            env_file.write_text(
                "".join(line + "\n" for line in full.splitlines()
                        if not line.startswith(missing + "=")),
                encoding="utf-8",
            )
            result = subprocess.run(
                [str(wrapper)], env=base_env,
                text=True, capture_output=True, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0, message)
            self.assertIn(message, result.stderr)
        env_file.write_text(full, encoding="utf-8")

    def test_shoukichi_wrapper_projects_identity_into_vibe_home(self) -> None:
        self.prepare_shoukichi()
        wrapper = HERE.parents[3] / "bin/shoukichi-telegram"
        vibe_home = self.home / ".config/vibe-telegram/vibe-home"
        # Pre-existing divergent identity must be overwritten.
        (vibe_home / "AGENTS.md").write_text("stale persona\n", encoding="utf-8")
        # The looping bridge fake would hang: the wrapper always execs it.
        self.write_exit_zero_bridge(self.shoukichi_bridge_py)
        result = subprocess.run(
            [str(wrapper)],
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home)},
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        projected = (vibe_home / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Shoukichi synthetic identity", projected)
        self.assertNotIn("stale persona", projected)
        self.assertEqual((vibe_home / "AGENTS.md").stat().st_mode & 0o777, 0o600)
        self.assertEqual(vibe_home.stat().st_mode & 0o777, 0o700)

    def test_shoukichi_vibe_home_config_pins_ask_and_glm(self) -> None:
        templates = HERE.parents[4] / ".bots/templates"
        config_text = (templates / "shoukichi-vibe-home-config.toml").read_text(encoding="utf-8")
        active_lines = [
            line for line in config_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertIn('default_agent = "ask"', active_lines)
        self.assertIn('active_model = "zai-glm-5-3"', active_lines)
        self.assertIn('allowed_models = ["zai-glm-5-3"]', active_lines)
        # The fixture fails the moment the pin falls back to accept-edits or
        # auto-approve (Fable's go-ahead, note 2) — checked on active lines;
        # the template's explanatory comments may name the refused modes.
        self.assertFalse(any("accept-edits" in line or "auto-approve" in line
                             for line in active_lines))
        # Model id is Mistral's exact zai-glm-5-3; no glm-5.3 alias exists.
        self.assertFalse(any("glm-5.3" in line for line in active_lines))

    def test_shoukichi_templates_hold_no_secrets(self) -> None:
        templates = HERE.parents[4] / ".bots/templates"
        for name in ("shoukichi-vibe-telegram.env", "shoukichi-vibe-telegram.conf",
                     "shoukichi-vibe-home-config.toml"):
            text = (templates / name).read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(r"bot[0-9]{8,}:[A-Za-z0-9_-]{30,}", text),
                name + " leaks a bot-token-shaped literal",
            )
        env_lines = (templates / "shoukichi-vibe-telegram.env").read_text(encoding="utf-8").splitlines()
        for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USER_IDS", "MISTRAL_VIBE_API_KEY"):
            self.assertIn(f"# {key}=", env_lines)
            self.assertFalse(any(line.startswith(key + "=") for line in env_lines))
        conf_lines = [
            line for line in (templates / "shoukichi-vibe-telegram.conf")
            .read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        conf_active = "\n".join(conf_lines)
        self.assertIn("VIBE_BRIDGE_LANG=en", conf_lines)
        self.assertIn("VIBE_BRIDGE_FORBIDDEN_MODES=auto-approve", conf_lines)
        # The HTTP automation endpoint stays disabled: no active line sets
        # the token (comments may explain its absence).
        self.assertNotIn("VIBE_BRIDGE_HTTP_TOKEN", conf_active)


if __name__ == "__main__":
    unittest.main()
