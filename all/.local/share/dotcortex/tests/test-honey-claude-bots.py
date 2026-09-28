#!/usr/bin/env python3
"""Tests for the Honey Telegram Claude bot launchers and services (agents-bots-honey.org)."""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
BIN = ROOT / "honey/.local/bin"
OPENRC = ROOT / "honey/.local/share/honey-claude/openrc"
SHARE = ROOT / "honey/.local/share/honey-claude"
BOTS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-4-6", "haiku": "claude-haiku-4-5-20251001"}
PERSONAS = {"opus": "Bunta", "sonnet": "Sasuke", "haiku": "Shoukichi"}


class Home:
    def __init__(self, plugin_enabled=True, boundary=True, account=True):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.bin = Path(self.tmp.name) / "bin"
        self.xdg = Path(self.tmp.name) / "run"
        self.record = Path(self.tmp.name) / "record.json"
        for path in (self.home, self.bin, self.xdg):
            path.mkdir()
        (self.home / ".claude").mkdir()
        if account:
            (self.home / ".claude.json").write_text(json.dumps({"oauthAccount": {"accountUuid": "test-account"}}))
        (self.home / ".claude/settings.json").write_text(
            json.dumps({"enabledPlugins": {"telegram@claude-plugins-official": plugin_enabled}}))
        plugin = self.home / ".claude/plugins/cache/claude-plugins-official/telegram/0.0.6"
        plugin.mkdir(parents=True)
        (plugin / ".mcp.json").write_text(json.dumps({"mcpServers": {"telegram": {"command": "bun"}}}))
        (plugin / "server.ts").write_text("")
        npm_bin = self.home / ".npm-global/bin"
        npm_bin.mkdir(parents=True)
        self.script(npm_bin / "bun", "exit 0\n")
        self.script(self.bin / "claude-warm", (
            "import json, os, sys\n"
            f"json.dump({{'argv': sys.argv[1:], 'cwd': os.getcwd(), 'pid': os.getpid(),"
            " 'agent': os.environ.get('CLAUDE_WARM_HERDR_AGENT'),"
            " 'state': os.environ.get('TELEGRAM_STATE_DIR'), 'path': os.environ['PATH'],"
            " 'guard': {k: v for k, v in os.environ.items() if k.startswith('CLAUDE_WARM_PRESERVATION_')}},"
            f" open({str(self.record)!r}, 'w'))\n"), shebang="#!/usr/bin/env python3\n")
        for bot in BOTS:
            state = self.home / f".claude/channels/telegram-{bot}"
            state.mkdir(parents=True)
            (state / ".env").write_text("TELEGRAM_BOT_TOKEN=dummy-test-value\n")
            work = self.home / "honey-work" / bot
            work.mkdir(parents=True)
            if boundary:
                (work / "CLAUDE.md").write_text((SHARE / f"CLAUDE.{bot}.md").read_text())

    @staticmethod
    def script(path, body, shebang="#!/bin/sh\n"):
        path.write_text(shebang + body)
        path.chmod(0o755)

    def run(self, bot, *args):
        env = {"HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin",
               "XDG_RUNTIME_DIR": str(self.xdg)}
        return subprocess.run([str(BIN / f"honey-{bot}"), *args], capture_output=True,
                              text=True, env=env)

    def recorded(self):
        return json.loads(self.record.read_text())

    def close(self):
        self.tmp.cleanup()


class LauncherTests(unittest.TestCase):
    def test_each_bot_launches_its_telegram_warm_session(self):
        box = Home()
        try:
            agents = set()
            for bot, model in BOTS.items():
                result = box.run(bot, "--telegram")
                self.assertEqual(result.returncode, 0, result.stderr)
                rec = box.recorded()
                self.assertEqual(rec["argv"], ["--model", model, "--permission-mode", "acceptEdits",
                                               "--allowedTools=mcp__plugin_telegram_telegram",
                                               "--settings=" + str(SHARE / "lib") + "/../claude-settings.json",
                                               "--channels", "plugin:telegram@claude-plugins-official"])
                self.assertEqual(rec["cwd"], str(box.home / "honey-work" / bot))
                self.assertEqual(rec["state"], str(box.home / f".claude/channels/telegram-{bot}"))
                self.assertEqual(rec["agent"], f"honey-{bot}-bot")
                self.assertIn(str(box.home / ".npm-global/bin"), rec["path"].split(":"))
                self.assertTrue(rec["path"].startswith(str(box.bin)), "PATH must be appended to")
                pidfile = box.xdg / f"honey-{bot}.pid"
                self.assertEqual(pidfile.read_text().strip(), str(rec["pid"]))
                agents.add(rec["agent"])
            self.assertNotIn("honey-opus", agents, "collides with Honey's existing warm consort")
        finally:
            box.close()

    def test_gillean_usage_guard_is_bound(self):
        import hashlib
        box = Home()
        try:
            result = box.run("sonnet", "--telegram")
            self.assertEqual(result.returncode, 0, result.stderr)
            guard = box.recorded()["guard"]
            self.assertEqual(len(guard), 18, sorted(guard))
            digest = "sha256:" + hashlib.sha256(b"test-account").hexdigest()
            self.assertEqual(guard["CLAUDE_WARM_PRESERVATION_ACCOUNT_HASH"], digest)
            self.assertEqual(guard["CLAUDE_WARM_PRESERVATION_AUTHORITY_IDENTITY"], "kikin-kushi")
            self.assertEqual(guard["CLAUDE_WARM_PRESERVATION_TELEMETRY_HOST"], "honey-metsatron")
            self.assertTrue(guard["CLAUDE_WARM_PRESERVATION_LEDGER_ROOT"].endswith("/claude-gillean"))
            self.assertTrue(guard["CLAUDE_WARM_PRESERVATION_BRIDGE"].endswith(
                "/skills-mirror/FORGE/bin/fleet-preservation"))
            self.assertNotIn("test-account", json.dumps(guard))
        finally:
            box.close()

    def test_guard_is_inert_but_bot_runs_before_login(self):
        box = Home(account=False)
        try:
            result = box.run("haiku", "--telegram")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("usage guard inert", result.stderr)
            self.assertEqual(box.recorded()["guard"], {})
        finally:
            box.close()

    def test_personas_in_identity_files(self):
        for bot, name in PERSONAS.items():
            text = (SHARE / f"CLAUDE.{bot}.md").read_text()
            self.assertTrue(text.startswith(f"# CLAUDE.md - {name} (honey-{bot}, @honey_{bot}_bot, {BOTS[bot]})"))
            self.assertIn("## Identity", text)
            self.assertIn("# Honey boundary law", text)
            self.assertIn(name, (BIN / f"honey-{bot}").read_text())

    def test_plain_run_has_no_channel(self):
        box = Home()
        try:
            result = box.run("haiku")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(box.recorded()["argv"], ["--model", BOTS["haiku"]])
        finally:
            box.close()

    def test_model_override(self):
        box = Home()
        try:
            env_run = subprocess.run([str(BIN / "honey-sonnet")], capture_output=True, text=True,
                                     env={"HOME": str(box.home), "PATH": f"{box.bin}:/usr/bin:/bin",
                                          "HONEY_SONNET_MODEL": "claude-sonnet-x"})
            self.assertEqual(env_run.returncode, 0, env_run.stderr)
            self.assertEqual(box.recorded()["argv"], ["--model", "claude-sonnet-x"])
        finally:
            box.close()

    def test_refuses_without_boundary_law(self):
        box = Home(boundary=False)
        try:
            result = box.run("opus", "--telegram")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("boundary law", result.stderr)
            self.assertFalse(box.record.exists())
        finally:
            box.close()

    def test_refuses_without_enabled_plugin(self):
        box = Home(plugin_enabled=False)
        try:
            result = box.run("opus", "--telegram")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not enabled", result.stderr)
            self.assertNotIn("dummy-test-value", result.stdout + result.stderr)
            self.assertFalse(box.record.exists())
        finally:
            box.close()


class ServiceTests(unittest.TestCase):
    def scripts(self):
        return {bot: (OPENRC / f"honey-{bot}").read_text() for bot in BOTS}

    def test_three_identical_scripts(self):
        texts = set(self.scripts().values())
        self.assertEqual(len(texts), 1)

    def test_script_rules(self):
        text = next(iter(self.scripts().values()))
        self.assertTrue(text.startswith("#!/sbin/openrc-run\n"))
        self.assertNotRegex(text, r"\bneed\s+net\b")
        self.assertIn("use net dns", text)
        self.assertNotRegex(text, r"(^|[\s;'\"])PATH=['\"]?/", "PATH must only be appended to")
        self.assertIn('PATH=\\"\\${PATH}:', text)
        self.assertIn(': "${bot_user:=agent-claude}"', text)
        self.assertIn("/DotCortex/honey/.local/bin/", text)
        self.assertNotIn("/home/gille", text)
        result = subprocess.run(["sh", "-n", str(OPENRC / "honey-opus")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_boundary_law_names_the_vault_and_no_addresses(self):
        text = "".join((SHARE / f"CLAUDE.{bot}.md").read_text() for bot in BOTS)
        self.assertIn("Secret Vault", text)
        self.assertIsNone(re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text))


if __name__ == "__main__":
    unittest.main()
