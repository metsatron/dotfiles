from __future__ import annotations

import json
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
        for pid_file in (
            self.state / "telegram-agents/ductor-supervise.pid",
            self.state / "gemma-pi-telegram/adapter.pid",
        ):
            if pid_file.exists():
                try:
                    os.killpg(int(pid_file.read_text()), signal.SIGTERM)
                except (ProcessLookupError, PermissionError, ValueError):
                    pass
        self.temp.cleanup()

    def read_start_ticks(self, pid: int) -> str:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
        return fields[19]

    def write_dsh_marker(self, pid: int, *, start_ticks: str | None = None, profile: str = "helmcortex-telegram") -> None:
        marker = self.state / "telegram-agents/deepseek-harness.ready"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({
            "schema": 1,
            "component": "dsh-telegram",
            "pid": pid,
            "start_ticks": start_ticks if start_ticks is not None else self.read_start_ticks(pid),
            "profile": profile,
            "provider": "neuralwatt",
            "model": "deepseek-v4-flash",
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
                        "model": "deepseek-v4-flash",
                    },
                }
            ),
            encoding="utf-8",
        )
        token = self.home / ".config/deepseek-harness-telegram/token"
        token.parent.mkdir(parents=True)
        token.write_text("fake-token\n", encoding="utf-8")
        token.chmod(0o600)
        key = self.home / ".config/helmcortex/neuralwatt.key"
        key.parent.mkdir(parents=True)
        key.write_text("fake-key\n", encoding="utf-8")
        key.chmod(0o600)
        settings_text = "\n".join(
            [
                "llm-pi-ai:",
                "  providers:",
                "    neuralwatt:",
                "      displayName: HelmCortex NeuralWatt",
                "      apiKeyEnv: NEURALWATT_API_KEY",
                "      api: openai-completions",
                "      baseURL: https://api.neuralwatt.com/v1",
                "      models:",
                "        - id: deepseek-v4-flash",
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
                "    model: deepseek-v4-flash",
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
                    "DSH_TELEGRAM_MODEL=deepseek-v4-flash",
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
            result = self.run_manager("status", "deepseek-harness", timeout=2)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("deepseek-harness: RUNNING", result.stdout)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_deepseek_harness_rejects_model_fallback_in_private_config(self) -> None:
        self.agents.joinpath("hosts.conf").write_text(f"{HOST}|deepseek-harness\n", encoding="utf-8")
        self.prepare_deepseek_harness([123])
        config = self.home / ".local/share/deepseek-harness-telegram/workspace/.pi/telegram.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        data["model"] = {"provider": "neuralwatt", "model": "deepseek-v4-flash-flex"}
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
            self.write_dsh_marker(proc.pid)
        profile_patch.write_text(
            "- id: agent-default-model\n"
            "  config:\n"
            "    provider: neuralwatt\n"
            "    model: deepseek-v4-flash\n",
            encoding="utf-8",
        )
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

        result = self.run_manager("start", "deepseek-harness", timeout=2)
        self.assertEqual(result.returncode, 1)
        self.assertIn("refusing credential egress", result.stderr)

    def test_deepseek_harness_scrubs_ambient_deepseek_credentials(self) -> None:
        manager_text = MANAGER.read_text(encoding="utf-8")
        provider_scrub = "-u DEEPSEEK_API_KEY -u DEEPSEEK_API_KEY_FILE -u NEURALWATT_API_KEY"
        self.assertGreaterEqual(manager_text.count(provider_scrub), 2)
        self.assertIn("env -u TELEGRAM_BOT_TOKEN " + provider_scrub, manager_text)
        self.assertNotIn('DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY"', manager_text)

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
        self.assertIn('DSH_TELEGRAM_READY_TIMEOUT="${DSH_TELEGRAM_READY_TIMEOUT:-60}"', manager_text)
        self.assertIn('telegram_bot_identity_validated', manager_text)
        self.assertIn('long_polling_owned', manager_text)
        self.assertNotIn('TELEGRAM_BOT_TOKEN', manager_text[manager_text.index('deepseek_harness_marker_matches'):manager_text.index('deepseek_harness_wait_ready')])
        self.assertNotIn('chatId', manager_text[manager_text.index('deepseek_harness_marker_matches'):manager_text.index('deepseek_harness_wait_ready')])


if __name__ == "__main__":
    unittest.main()
        self.assertNotIn('NEURALWATT_API_KEY="$NEURALWATT_API_KEY"', manager_text)
        self.assertNotIn('TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN"', manager_text)
