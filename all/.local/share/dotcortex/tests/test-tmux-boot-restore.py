#!/usr/bin/env python3
import pathlib
import unittest


REPO = pathlib.Path(__file__).resolve().parents[5]
SOURCE = (REPO / "mux.org").read_text(encoding="utf-8")
TMUX_BEHAVIOR = (REPO / "all/.config/tmux/behavior.conf").read_text(encoding="utf-8")
BOOT = (REPO / "all/.local/bin/tmux-boot-restore").read_text(encoding="utf-8")
CRON_APPLY = (REPO / "all/.local/bin/tmux-boot-restore-cron-apply").read_text(encoding="utf-8")


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
            "Claude bot lifecycle belongs to Nurse Joy",
            "PATH=${TARGET_HOME}/.bun/bin:",
            "restore confirmed: all four Claude Telegram agents ready",
        ):
            self.assertIn(marker, SOURCE)


if __name__ == "__main__":
    unittest.main()
