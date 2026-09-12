from __future__ import annotations

import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time
import unittest


HERE = Path(__file__).resolve()
MANAGER = HERE.parents[3] / "bin" / "telegram-agent-host"
HOST = subprocess.check_output(["hostname"], text=True).strip().lower()


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

    def tearDown(self) -> None:
        pid_file = self.state / "telegram-agents/ductor-supervise.pid"
        if pid_file.exists():
            try:
                os.killpg(int(pid_file.read_text()), signal.SIGTERM)
            except (ProcessLookupError, PermissionError, ValueError):
                pass
        self.temp.cleanup()

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
        }
        return env

    def run_manager(self, *args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(MANAGER), *args], text=True, capture_output=True,
                              env=self.environment(timeout), timeout=timeout + 5)

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


if __name__ == "__main__":
    unittest.main()
