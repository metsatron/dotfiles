#!/usr/bin/env python3
import json
import os
import pathlib
import stat
import subprocess
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[5]
SOURCE = (REPO / "mux.org").read_text(encoding="utf-8")
TMUX_BEHAVIOR = (REPO / "all/.config/tmux/behavior.conf").read_text(encoding="utf-8")
BOOT = (REPO / "all/.local/bin/tmux-boot-restore").read_text(encoding="utf-8")
CRON_APPLY = (REPO / "all/.local/bin/tmux-boot-restore-cron-apply").read_text(encoding="utf-8")
FABLE_LAUNCHER = REPO / "all/.local/bin/tmux-fable-launch"
TELEGRAM_BOOT = (REPO / "all/.local/bin/telegram-agent-boot").read_text(encoding="utf-8")
TELEGRAM_HOSTS = (REPO / "all/.bots/hosts.conf").read_text(encoding="utf-8")


class TmuxBootRestoreContract(unittest.TestCase):
    def test_resurrect_does_not_replay_claude_warm(self):
        option = next(
            line for line in TMUX_BEHAVIOR.splitlines()
            if line.startswith("set -g @resurrect-processes ")
        )
        self.assertNotIn("claude-warm", option)

    def test_bare_boot_path_contains_bun(self):
        self.assertIn("PATH=${TARGET_HOME}/.bun/bin:", CRON_APPLY)

    def test_all_four_seats_are_required(self):
        self.assertIn('BOT_NAMES="Auryn Fable Haiku Opus"', BOOT)
        self.assertIn('tmux has-session -t "$bot"', BOOT)
        self.assertNotIn("grep -qE '^(Fable|Auryn|Opus|Haiku):'", BOOT)

    def test_boot_uses_durable_resume_through_nurse_joy(self):
        self.assertIn('last-session.${1}.json', BOOT)
        self.assertIn('"$NURSE_JOY" revive "$bot" --resume "$session_id" --no-visit', BOOT)
        self.assertIn("all four Claude Telegram agents ready", BOOT)

    def test_fable_fixture_launches_latest_session_through_wrapper(self):
        latest = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            state = root / "state" / "claude-idle-compaction"
            state.mkdir(parents=True)
            (state / "last-session.Fable.json").write_text(
                json.dumps({"session_id": latest}) + "\n", encoding="utf-8"
            )
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_tmux = fake_bin / "tmux"
            fake_tmux.write_text(
                "#!/usr/bin/env bash\n"
                "case \"$1\" in\n"
                "  list-panes) printf '%s\\n' '%2' ;;\n"
                "  display-message) printf '%s\\n' 'bash' ;;\n"
                "  send-keys) printf '%s\\n' \"$*\" >> \"$TMUX_FIXTURE_LOG\" ;;\n"
                "  *) exit 2 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            fake_claude = fake_bin / "claude-fable"
            fake_claude.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            for executable in (fake_tmux, fake_claude):
                executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            calls = root / "calls"
            env = os.environ.copy()
            env.update({
                "HOME": str(root),
                "XDG_STATE_HOME": str(root / "state"),
                "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
                "TMUX_FIXTURE_LOG": str(calls),
            })
            result = subprocess.run(
                [str(FABLE_LAUNCHER), "--latest"],
                text=True,
                capture_output=True,
                env=env,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                f"claude-fable --telegram --mailcortex --remote --resume {latest}",
                calls.read_text(encoding="utf-8"),
            )

    def test_fable_is_single_owner_other_seats_keep_nurse_joy(self):
        self.assertIn('FABLE_LAUNCHER="$HOME/.local/bin/tmux-fable-launch"', BOOT)
        self.assertIn('"$FABLE_LAUNCHER" --latest', BOOT)
        self.assertIn('OTHER_BOT_NAMES="Auryn Haiku Opus"', BOOT)
        self.assertNotIn('"$NURSE_JOY" revive "Fable"', BOOT)
        for bot in ("Auryn", "Haiku", "Opus"):
            self.assertIn(f'"$NURSE_JOY" revive "$bot" --resume "$session_id" --no-visit', BOOT)

    def test_telegram_boot_owner_does_not_start_fable(self):
        self.assertIn('enabled="$($MANAGER enabled)"', TELEGRAM_BOOT)
        self.assertNotIn("claude-fable", TELEGRAM_BOOT)
        self.assertNotIn("fable", TELEGRAM_HOSTS.casefold())

    def test_network_and_runtime_dependencies_gate_revival(self):
        for requirement in (
            "command -v bun",
            "command -v python3",
            "api.telegram.org",
            "api.anthropic.com",
            "CLAUDE_IDLE_REAL_EXECUTABLE",
        ):
            self.assertIn(requirement, BOOT)

    def test_source_owns_the_generated_contract(self):
        for marker in (
            "Claude bot lifecycle belongs to tmux-boot-restore",
            "PATH=${TARGET_HOME}/.bun/bin:",
            "restore confirmed: all four Claude Telegram agents ready",
        ):
            self.assertIn(marker, SOURCE)


if __name__ == "__main__":
    unittest.main()
