#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


REPO = Path(__file__).resolve().parents[5]
HOOK = REPO / "all/.local/bin/claude-hook-permission-request-kikin"
ENGINE = REPO / "all/.local/lib/dotcortex/claude_approval_kikin.py"


def event(tool_name, tool_input, cwd):
    return {"hook_event_name": "PermissionRequest", "tool_name": tool_name, "tool_input": tool_input, "cwd": str(cwd)}


def run_hook(payload, manifest, log=os.devnull):
    # Never let a test write the real decision ledger; os.devnull unless a test reads it.
    env = {**os.environ, "SO_APPROVAL_KIKIN_MANIFEST": str(manifest), "SO_APPROVAL_KIKIN_LOG": str(log)}
    return subprocess.run([str(HOOK)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=2, check=False)


def decision(completed):
    if not completed.stdout.strip():
        return "ask"
    return json.loads(completed.stdout)["hookSpecificOutput"]["decision"]["behavior"]


class KikinApprovalHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = json.loads((REPO / "all/.config/dotcortex/claude-approval-canary.kikin.v1.json").read_text())
        self.root = Path(self.temp.name) / "DotCortex"
        (self.root / "FORGE/bin").mkdir(parents=True)
        (self.root / ".git").mkdir()
        (self.root / "README.md").write_text("synthetic\n")
        (self.root / "FORGE/bin/pokemon-centre").write_text("synthetic\n")
        (self.root / "FORGE/bin/clubhouse-bosses-refresh").write_text("synthetic\n")
        self.scratch = Path(self.temp.name) / "scratch"
        self.scratch.mkdir()
        self.message = self.scratch / "message"
        self.message.write_text("test: synthetic\n")
        os.chmod(self.message, 0o600)

    def manifest(self, *enabled):
        data = json.loads(json.dumps(self.base))
        data["roots"] = [str(self.root)]
        data["scratch_roots"] = [str(self.scratch)]
        for item in data["classes"]:
            item["enabled"] = item["name"] in enabled
        path = self.scratch / "manifest.json"
        path.write_text(json.dumps(data))
        return path

    def assert_decision(self, payload, manifest, expected):
        completed = run_hook(payload, manifest)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(decision(completed), expected, completed.stdout)

    def test_decision_ledger_records_reason_without_tool_input(self):
        log = self.scratch / "decisions.jsonl"
        secret_path = str(self.root / "README.md")
        run_hook(event("Read", {"file_path": secret_path}, self.root), self.manifest("local_read"), log)
        run_hook(event("Read", {"file_path": secret_path}, self.root), self.manifest(), log)
        run_hook("not json", self.manifest(), log)
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual([(r["decision"], r["reason"]) for r in records],
                         [("allow", "local_read"), ("ask", "local_read_disabled"), ("ask", "not_permission_request")])
        self.assertNotIn(secret_path, log.read_text())
        self.assertEqual(oct(log.stat().st_mode & 0o777), "0o600")

    def test_compound_reads_allow_and_anything_else_asks(self):
        manifest = self.manifest("local_read", "git_observe")
        root = str(self.root)
        allow = [
            f"cd {root} && cat README.md",
            f"cd {root} && sed -n 1,2p README.md | cut -c1-200",
            "grep -n synthetic README.md | head -n 5",
            "cat README.md | wc -l",
            "git status --short && git log --oneline -1",
            "head -n 3 README.md; tail -1 README.md",
            "grep -n 'a|b' README.md | sort -n | uniq -c",
            "grep -n -i -E 'synth\\.etic|x' README.md 2>/dev/null | head -5",
            "timeout 30 grep -n synthetic README.md; echo === ; cat README.md 2>&1 | wc -l",
            "cat README.md 2>/dev/null || true",
            f"cd {root} && ls -la FORGE/bin | grep -iE 'poke|club'",
            "grep -il synthetic README.md",
        ]
        for command in allow:
            with self.subTest(allow=command):
                self.assert_decision(event("Bash", {"command": command, "description": "read"}, self.root), manifest, "allow")
        ask = [
            "cat README.md > copy",
            "cat README.md | tee copy",
            "cat README.md | sh",
            "git status | xargs rm",
            "cat README.md; rm README.md",
            "cat README.md && curl https://example.invalid",
            "cat README.md | sort -o copy",
            "cat README.md & ls",
            "cat $(echo README.md) | head",
            "cd / && cat etc/passwd",
            f"cat README.md || cd {root}",
            f"cd {root} && sed -n '1p;w copy' README.md",
            "sed -n 1p README.md | sed -i s/a/b/ README.md",
            "cat README.md | head -n 5 README.md",
            "cat README.md |",
            "cat 'README.md && ls",
            "printf x && cat README.md",
            'grep -n "$(id)" README.md',
            'grep -n "a\\$b" README.md | head',
            "cat README.md 2>/tmp/err",
            "cat README.md >/dev/null; cat README.md > copy",
            "timeout 30 rm README.md && cat README.md",
            "echo x | sh",
            "grep -rn synthetic . | head",
            "ls -la / && cat README.md",
        ]
        for command in ask:
            with self.subTest(ask=command):
                self.assert_decision(event("Bash", {"command": command}, self.root), manifest, "ask")
        # A compound read still respects a disabled class.
        self.assert_decision(event("Bash", {"command": "cat README.md | wc -l"}, self.root), self.manifest(), "ask")

    def test_all_classes_are_default_off(self):
        manifest = REPO / "all/.config/dotcortex/claude-approval-canary.kikin.v1.json"
        self.assertTrue(all(not item["enabled"] for item in self.base["classes"]))
        self.assert_decision(event("Read", {"file_path": str(self.root / "README.md")}, self.root), manifest, "ask")

    def test_each_class_has_green_and_disabled_paths(self):
        cases = [
            ("local_read", event("Read", {"file_path": str(self.root / "README.md")}, self.root)),
            ("git_observe", event("Bash", {"command": "git status --short"}, self.root)),
            ("centre_render", event("Bash", {"command": "FORGE/bin/pokemon-centre render"}, self.root)),
            ("safe_commit", event("Bash", {"command": f"git commit -F {self.message} -- README.md"}, self.root)),
        ]
        for class_name, payload in cases:
            with self.subTest(class_name=class_name):
                self.assert_decision(payload, self.manifest(class_name), "allow")
                self.assert_decision(payload, self.manifest(), "ask")

    def test_full_red_corpus_never_allows(self):
        manifest = self.manifest("local_read", "git_observe", "centre_render", "safe_commit")
        commands = [
            "cat .env", "cat NEXUS/keys/token", "cat LOGS/Telegram/Personal/chat.md",
            "cat CORTEX/PalmCortex/Diary.md", "git show HEAD:NEXUS/.secrets/token",
            "ssh kikin date", "scp x kikin:/tmp/x", "sudo true", "crontab -l",
            "telegram-agent-host stop fable", "nurse-joy revive Fable", "tmux kill-server",
            "pkill python3", "kill -9 123", "kill", "pip install x", "apt install x",
            "cat README.md > /tmp/copy", "find . -exec cat {} +", "find . -delete",
            "git push", "git reset --keep HEAD~1", "rm -rf README.md", "cat $(printf README.md)",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_decision(event("Bash", {"command": command}, self.root), manifest, "ask")

    def test_mount_symlink_and_scratch_output_boundaries(self):
        mount = Path(self.temp.name) / "mount"
        mount.mkdir()
        (mount / "README.md").write_text("mounted\n")
        (mount / ".git").mkdir()
        canonical = Path(self.temp.name) / "HelmCortex"
        canonical.symlink_to(mount, target_is_directory=True)
        data = json.loads(self.manifest("local_read").read_text())
        data["roots"] = [str(canonical)]
        manifest = self.scratch / "mount.json"
        manifest.write_text(json.dumps(data))
        self.assert_decision(event("Read", {"file_path": str(canonical / "README.md")}, canonical), manifest, "allow")
        data["classes"][-2]["enabled"] = True
        manifest.write_text(json.dumps(data))
        self.assert_decision(event("Bash", {"command": "FORGE/bin/pokemon-centre render --out /etc/x"}, canonical), manifest, "ask")

    def _decider_manifest(self, *, honey=None, kikin=None, enabled=True):
        data = json.loads(self.manifest("local_read", "git_observe").read_text())
        data["manifest_version"] = "claude-approval-canary.kikin.v2"
        data["decider"] = {
            "enabled": enabled,
            "honey_url": honey,
            "kikin_url": kikin,
            "timeout_ms": 800,
            "min_allow_confidence": 0.95,
            "questions": "single",
        }
        path = self.scratch / "manifest-decider.json"
        path.write_text(json.dumps(data))
        return path

    def _c1_answers(self, *, allow=True):
        # Single-mode contract: noul = P(sensitive). allow → 0.02 (98% confident
        # not sensitive), deny → 0.9 (only 10% confident).
        return {"approval.sensitive_effect.v1": {"type": "noul", "noul": 0.02 if allow else 0.9}}

    def _fake_decider(self, answers=None, *, status=200, delay=0.0):
        import http.server
        import threading

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                if delay:
                    time.sleep(delay)
                if answers is None:
                    body = "{}"
                else:
                    body = json.dumps({"model_sha256": "b7c132a67934d51c81abc96bb7724800f965ff5a288aed3e1ca7d8bc349c1386", "answers": answers})
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        server.threshold = 0.95
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}/v1/systemone"

    def test_decider_allow_enables_grey_zone(self):
        url = self._fake_decider(self._c1_answers(allow=True))
        manifest = self._decider_manifest(kikin=url)
        log = self.scratch / "decider.jsonl"
        payload = event("Bash", {"command": "cat README.md > copy"}, self.root)
        run_hook(payload, manifest, log)
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(records[-1]["decision"], "allow")
        self.assertEqual(records[-1]["reason"], "decider_allow")
        self.assertEqual(records[-1]["decider_status"], "accepted")
        self.assertEqual(records[-1]["verdict"], "allow")
        self.assertIsInstance(records[-1]["latency_ms"], int)

    def test_decider_denied_asks(self):
        url = self._fake_decider(self._c1_answers(allow=False))
        manifest = self._decider_manifest(kikin=url)
        log = self.scratch / "decider.jsonl"
        run_hook(event("Bash", {"command": "cat README.md > copy"}, self.root), manifest, log)
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(records[-1]["decision"], "ask")
        self.assertEqual(records[-1]["decider_status"], "threshold_failed")

    def test_decider_down_asks(self):
        manifest = self._decider_manifest(kikin="http://127.0.0.1:1/v1/systemone")
        log = self.scratch / "decider.jsonl"
        run_hook(event("Bash", {"command": "cat README.md > copy"}, self.root), manifest, log)
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(records[-1]["decision"], "ask")
        self.assertEqual(records[-1]["decider_status"], "unavailable")

    def test_decider_timeout_asks(self):
        url = self._fake_decider(self._c1_answers(allow=True), delay=3.0)
        manifest = self._decider_manifest(kikin=url)
        log = self.scratch / "decider.jsonl"
        run_hook(event("Bash", {"command": "cat README.md > copy"}, self.root), manifest, log)
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(records[-1]["decision"], "ask")
        self.assertEqual(records[-1]["decider_status"], "timeout")

    def test_true_floor_cannot_be_overridden(self):
        url = self._fake_decider(self._c1_answers(allow=True))
        manifest = self._decider_manifest(kikin=url)
        log = self.scratch / "decider.jsonl"
        floor_commands = [
            "ssh kikin date", "sudo true", "pkill python3", "kill -9 123",
            "pip install x", "rm -rf README.md", "cat .env", "cat NEXUS/keys/token",
        ]
        for command in floor_commands:
            with self.subTest(command=command):
                run_hook(event("Bash", {"command": command}, self.root), manifest, log)
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertTrue(all(record["decision"] == "ask" for record in records[-len(floor_commands):]))
        self.assertTrue(all(record["reason"] == "true_floor" for record in records[-len(floor_commands):]))
        self.assertNotIn("decider_status", records[-1])

    def test_decider_disabled_keeps_grey_zone_asking(self):
        manifest = self._decider_manifest(enabled=False)
        log = self.scratch / "decider.jsonl"
        run_hook(event("Bash", {"command": "cat README.md > copy"}, self.root), manifest, log)
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(records[-1]["decision"], "ask")
        self.assertNotIn("decider_status", records[-1])

    def test_v1_manifest_still_loads_without_decider(self):
        manifest = self.manifest("local_read")
        self.assert_decision(event("Read", {"file_path": str(self.root / "README.md")}, self.root), manifest, "allow")

    def test_malformed_input_asks(self):
        manifest = self.manifest("local_read")
        completed = subprocess.run([str(HOOK)], input="{not-json", text=True, capture_output=True, env={**os.environ, "SO_APPROVAL_KIKIN_MANIFEST": str(manifest), "SO_APPROVAL_KIKIN_LOG": os.devnull}, timeout=2, check=False)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(decision(completed), "ask")


if __name__ == "__main__":
    unittest.main()
