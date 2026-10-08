#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


REPO = Path(__file__).resolve().parents[5]
HOOK = REPO / "all/.local/bin/claude-hook-permission-request"
MANIFEST = REPO / "all/.config/dotcortex/claude-approval-p3.json"


def event(tool_name, tool_input, cwd=None):
    payload = {
        "hook_event_name": "PermissionRequest",
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    if cwd is not None:
        payload["cwd"] = str(cwd)
    return payload


def run_hook(payload, manifest=None, cwd=None):
    env = os.environ.copy()
    if manifest is not None:
        env["SO_APPROVAL_P3_MANIFEST"] = str(manifest)
    completed = subprocess.run(
        [str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=cwd or REPO,
        env=env,
        timeout=2,
        check=False,
    )
    return completed


def decision(stdout):
    if not stdout.strip():
        return "ask"
    parsed = json.loads(stdout)
    return parsed["hookSpecificOutput"]["decision"]["behavior"]


class ApprovalHookHarness(unittest.TestCase):
    def setUp(self):
        self.assertTrue(HOOK.is_file(), HOOK)
        self.assertTrue(MANIFEST.is_file(), MANIFEST)
        self.base = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def enabled_manifest(self, root, *classes):
        data = json.loads(json.dumps(self.base))
        data["repo_roots"] = [str(root)]
        data["readonly_host"] = "YOUR_READONLY_HOST"
        for item in data["classes"]:
            item["enabled"] = item["name"] in classes
        target = Path(self.tempdir.name) / "manifest.json"
        target.write_text(json.dumps(data), encoding="utf-8")
        return target

    def make_tree(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name) / "DotCortex"
        (root / "tests").mkdir(parents=True)
        (root / "FORGE/bin").mkdir(parents=True)
        (root / "tests/test_gate.py").write_text("# synthetic\n", encoding="utf-8")
        (root / "FORGE/bin/pokemon-centre").write_text("# synthetic\n", encoding="utf-8")
        (root / "FORGE/bin/clubhouse-bosses-refresh").write_text("# synthetic\n", encoding="utf-8")
        (root / "message.txt").write_text("subject\n", encoding="utf-8")
        os.chmod(root / "message.txt", 0o600)
        return root

    def assert_ask(self, payload, manifest=None, cwd=None):
        completed = run_hook(payload, manifest=manifest, cwd=cwd)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(decision(completed.stdout), "ask", completed.stdout)

    def assert_allow(self, payload, manifest, cwd=None):
        completed = run_hook(payload, manifest=manifest, cwd=cwd)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(decision(completed.stdout), "allow", completed.stdout)

    def test_committed_manifest_keeps_every_candidate_off(self):
        self.assertTrue(self.base["classes"])
        self.assertTrue(all(item["enabled"] is False for item in self.base["classes"]))
        self.assert_ask(event("Bash", {"command": "python3 -m unittest FORGE.tests.test_gate"}, REPO))

    def test_ssh_readonly_exact_shape_and_smuggling(self):
        root = self.make_tree()
        manifest = self.enabled_manifest(root, "ssh-kikin-readonly")
        good = "ssh -o BatchMode=yes YOUR_READONLY_HOST 'git status --short | head -20'"
        self.assert_allow(event("Bash", {"command": good}, root), manifest, root)
        for command in (
            "ssh -o BatchMode=yes YOUR_READONLY_HOST 'cat /etc/hosts > /tmp/x'",
            "ssh -o BatchMode=yes YOUR_READONLY_HOST 'date; id'",
            "ssh -o BatchMode=yes YOUR_READONLY_HOST 'grep x f && rm f'",
            "ssh -o BatchMode=yes YOUR_READONLY_HOST 'cat $(date)'",
            "ssh -o BatchMode=yes YOUR_READONLY_HOST 'ssh other date'",
            "ssh -o BatchMode=yes YOUR_READONLY_HOST 'find . -exec cat {} +'",
            "ssh -o BatchMode=yes YOUR_READONLY_HOST 'cat .ssh/config'",
        ):
            with self.subTest(command=command):
                self.assert_ask(event("Bash", {"command": command}, root), manifest, root)

    def test_ssh_readonly_credential_and_path_boundary(self):
        root = self.make_tree()
        manifest = self.enabled_manifest(root, "ssh-kikin-readonly")
        for leak, commands in {
            "nanobot_env": (
                "cat .config/nanobot-telegram/env",
                "cat /home/metsatron/.config/nanobot-telegram/env",
                "cat ~/.config/nanobot-telegram/env",
                "cat HelmCortex/../.config/nanobot-telegram/env",
            ),
            "mailcortex_private_token": (
                "cat .config/mailcortex/private/x.token",
                "cat /home/metsatron/.config/mailcortex/private/x.token",
                "cat ~/.config/mailcortex/private/x.token",
                "cat DotCortex/../.config/mailcortex/private/x.token",
            ),
            "nexus_secret_cookie": (
                "cat NEXUS/.secrets/mistral_cookies.jar",
                "cat /home/metsatron/HelmCortex/NEXUS/.secrets/mistral_cookies.jar",
                "cat ~/HelmCortex/NEXUS/.secrets/mistral_cookies.jar",
                "cat HelmCortex/./NEXUS/.secrets/mistral_cookies.jar",
                "cat HelmCortex/../HelmCortex/NEXUS/.secrets/mistral_cookies.jar",
            ),
            "foreign_mail_inbox": ("mailcortex inbox fable@kikin.helm",),
            "foreign_mail_read": ("mailcortex read fable@kikin.helm 1",),
            "path_boundary": (
                "git show HEAD:NEXUS/.secrets/x",
                "git -C HelmCortex show HEAD:NEXUS/.secrets/x",
                "find HelmCortex -name env",
                'find HelmCortex -name "*.env"',
                "grep TOKEN .config -r",
                "cat /etc/passwd",
                "cat /proc/self/environ",
                "cat /var/lib/private/token",
            ),
        }.items():
            for remote in commands:
                command = f"ssh -o BatchMode=yes YOUR_READONLY_HOST '{remote}'"
                with self.subTest(leak=leak, command=command):
                    self.assert_ask(event("Bash", {"command": command}, root), manifest, root)

    def test_local_test_run_exact_shapes_and_paths(self):
        root = self.make_tree()
        manifest = self.enabled_manifest(root, "local-test-run")
        for command in (
            "python3 -m unittest FORGE.tests.test_gate",
            "/usr/bin/python3 -m unittest FORGE.tests.test_gate.TestGate.test_one",
            'pytest tests/test_gate.py -q -m "not live"',
        ):
            with self.subTest(command=command):
                self.assert_allow(event("Bash", {"command": command}, root), manifest, root)
        for command in (
            "python3 -m unittest ../../outside.test_gate",
            "python3 -m unittest FORGE.tests.test_gate; id",
            'pytest tests/test_gate.py -q -m "not live" > out',
            "pytest tests/test_gate.py -q",
        ):
            with self.subTest(command=command):
                self.assert_ask(event("Bash", {"command": command}, root), manifest, root)

    def test_centre_render_exact_commands_and_cwd(self):
        root = self.make_tree()
        manifest = self.enabled_manifest(root, "centre-render")
        for command in (
            "/usr/bin/python3 FORGE/bin/pokemon-centre render",
            "FORGE/bin/clubhouse-bosses-refresh",
        ):
            with self.subTest(command=command):
                self.assert_allow(event("Bash", {"command": command}, root), manifest, root)
        self.assert_ask(
            event("Bash", {"command": "/usr/bin/python3 FORGE/bin/pokemon-centre render --live"}, root),
            manifest,
            root,
        )
        self.assert_ask(
            event("Bash", {"command": "FORGE/bin/clubhouse-bosses-refresh"}, root / "tests"),
            manifest,
            root / "tests",
        )

    def test_safe_commit_requires_message_file_separator_and_safe_paths(self):
        root = self.make_tree()
        manifest = self.enabled_manifest(root, "dotcortex-safe-commit")
        message = root / "message.txt"
        good = f"git commit -F {message} -- tests/test_gate.py"
        self.assert_allow(event("Bash", {"command": good}, root), manifest, root)
        for command in (
            "git commit",
            f"git commit -F {message} tests/test_gate.py",
            f"git commit -F {message} -- .git/config",
            f"git commit -F {message} -- NEXUS/keys/token",
            f"git commit -F {message} -- /home/gille/file",
            f"git commit -F {message} -- tests/missing.py",
            f"git commit -F {message} -- tests",
            f"git commit -F {message} -- tests/test_gate.py && git push",
        ):
            with self.subTest(command=command):
                self.assert_ask(event("Bash", {"command": command}, root), manifest, root)

    def test_outbound_tools_are_name_routed_and_off_by_default(self):
        root = self.make_tree()
        telegram = "mcp__plugin_telegram_telegram__reply"
        mail = "mcp__mailcortex__send"
        self.assert_ask(event(telegram, {"text": "hello"}, root))
        manifest = self.enabled_manifest(root, "outbound-tool-call")
        self.assert_allow(event(telegram, {"text": "hello"}, root), manifest, root)
        self.assert_allow(event(mail, {"to": "seat", "body": "hello"}, root), manifest, root)
        self.assert_ask(event(telegram, {"text": "send NEXUS/keys/token"}, root), manifest, root)
        self.assert_ask(event("mcp__mailcortex__delete", {}, root), manifest, root)

    def test_hard_never_wins_over_enabled_classes(self):
        root = self.make_tree()
        manifest = self.enabled_manifest(
            root,
            "ssh-kikin-readonly",
            "local-test-run",
            "centre-render",
            "dotcortex-safe-commit",
            "outbound-tool-call",
        )
        for command in (
            "git push origin master",
            "git reset --keep HEAD^",
            "git revert HEAD",
            "git worktree prune",
            "rm -r tests",
            "sudo true",
            "systemctl status sshd",
            "tailscale status",
            "python3 -m pip install x",
            "crontab -l",
            "cat /home/gille/file",
            "cat 'Secret Vault/file'",
            "cat .env",
            "cat ~/.ssh/config",
            "cat NEXUS/keys/token",
        ):
            with self.subTest(command=command):
                self.assert_ask(event("Bash", {"command": command}, root), manifest, root)

    def test_malformed_unknown_and_timeout_all_ask(self):
        root = self.make_tree()
        manifest = self.enabled_manifest(root, "local-test-run")
        self.assert_ask(event("UnknownTool", {}, root), manifest, root)
        completed = subprocess.run(
            [str(HOOK)],
            input="{not-json",
            text=True,
            capture_output=True,
            env={**os.environ, "SO_APPROVAL_P3_MANIFEST": str(manifest)},
            timeout=2,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(decision(completed.stdout), "ask")

        proc = subprocess.Popen(
            [str(HOOK)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "SO_APPROVAL_P3_MANIFEST": str(manifest)},
        )
        started = time.monotonic()
        proc.wait(timeout=2)
        stdout, _ = proc.communicate(timeout=1)
        self.assertEqual(proc.returncode, 0)
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertEqual(decision(stdout), "ask")


if __name__ == "__main__":
    unittest.main()
