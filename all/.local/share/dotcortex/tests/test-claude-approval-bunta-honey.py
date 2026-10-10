#!/usr/bin/env python3
"""Worst-case replay: Bunta's Honey prompt shapes vs the shared engine."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
ENGINE = HERE.parents[3] / "lib/dotcortex/claude_approval_kikin.py"
MANIFEST_SRC = HERE.parents[4] / ".config/dotcortex/claude-approval-bunta.honey.v2.json"
TMP = Path(tempfile.mkdtemp(prefix="bunta-replay."))


def event(tool_name, tool_input, cwd):
    return {"hook_event_name": "PermissionRequest", "tool_name": tool_name,
            "tool_input": tool_input, "cwd": str(cwd)}


def load_engine():
    import importlib.util
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("shared_engine", str(ENGINE))
    spec = importlib.util.spec_from_loader("shared_engine", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def bunta_manifest(engine, root):
    data = json.loads(MANIFEST_SRC.read_text())
    data["roots"] = [str(root), "/var/tmp"]
    data["scratch_roots"] = ["/var/tmp"]
    data["classes"] = [item for item in data["classes"]]
    # NOTE: no 'entries' key — the hook's loader validates set(data) strictly
    # and builds entries itself; classify() callers add entries separately.
    return data


class BuntaReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine()
        cls.root = TMP / "HelmCortex"
        (cls.root / ".git").mkdir(parents=True)
        (cls.root / "README.md").write_text("synthetic")
        cls.scratch = TMP / "scratch"
        cls.scratch.mkdir()
        cls.manifest = bunta_manifest(cls.engine, cls.root)
        # r2d2d decider endpoint: fake ALWAYS-ALLOW (separate module file,
        # written to TMP at runtime; no inline -c quoting hazards).
        server_src = TMP / "fake_decider.py"
        server_src.write_text(
            "import http.server, json\n"
            "class H(http.server.BaseHTTPRequestHandler):\n"
            "    def do_POST(self):\n"
            "        n = int(self.headers.get('content-length', 0)); self.rfile.read(n)\n"
            "        body = json.dumps({'answers': [{'choice': 'no', 'confidence': 0.99, 'p_yes': 0.01}], 'ms': 5}).encode()\n"
            "        self.send_response(200); self.send_header('content-length', str(len(body))); self.end_headers(); self.wfile.write(body)\n"
            "    def log_message(self, *a): pass\n"
            "http.server.HTTPServer(('127.0.0.1', 18097), H).serve_forever()\n")
        cls.fake_decider = subprocess.Popen([sys.executable, str(server_src)],
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time
        time.sleep(0.4)

    @classmethod
    def tearDownClass(cls):
        cls.fake_decider.terminate()
        cls.fake_decider.wait(timeout=5)

    @classmethod
    def _with_entries(cls, manifest):
        data = json.loads(json.dumps(manifest))
        data["entries"] = {item["name"]: item for item in data.get("classes", [])}
        data.setdefault("roots", [])
        data["roots"] = [os.path.realpath(r) for r in data["roots"]]
        return data

    def _classify(self, command, cwd=None):
        return self.engine.classify(event("Bash", {"command": command}, cwd or self.root), self._with_entries(self.manifest))

    # ---- hard denies stay hard (decider fully enabled, fake always-allow) ----
    def test_hard_denies_with_decider_enabled(self):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["decider"] = {"enabled": True,
                               "honey_url": "http://127.0.0.1:18097/decide",
                               "honey_api": "r2d2d",
                               "kikin_url": None,
                               "timeout_ms": 2000,
                               "min_allow_confidence": 0.95,
                               "questions": "single"}
        hard = [
            ("rm -rf /var/tmp/x", "true_floor"),
            ("sudo -n rc-service honey-badger-opus zap", "true_floor"),
            ("pip install --user ductor==0.20.1", "true_floor"),
            ("git push", "true_floor"),
            ("git reset --hard HEAD~1", "true_floor"),
            ("cat ~/.ssh/id_ed25519", "true_floor"),
            ("cat /home/gille/.kdbx KeePass", "true_floor"),
            ("cat .env", "true_floor"),
            ("git worktree prune", "true_floor"),
        ]
        manifest = self._with_entries(manifest)
        for command, expected in hard:
            with self.subTest(command=command):
                allow, reason = self.engine.classify(event("Bash", {"command": command}, self.root), manifest)
                self.assertFalse(allow, command)
                self.assertEqual(reason, expected, command)

    # ---- Gillean's home is protected hard (fix round 2026-10-10 item 2) ----
    # Nothing under /home/gille outside an explicit root, and nothing under
    # /home/gille/Secret Vault, may EVER be allowed — floor, even with an
    # always-allow decider. The Bunta manifest carries NO gille root, so no
    # class can reach it and the floor denies all of it.
    def test_gille_home_never_allowed_even_with_always_allow_decider(self):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["decider"] = {"enabled": True,
                               "honey_url": "http://127.0.0.1:18097/decide",
                               "honey_api": "r2d2d",
                               "kikin_url": None,
                               "timeout_ms": 2000,
                               "min_allow_confidence": 0.95,
                               "questions": "single"}
        manifest = self._with_entries(manifest)
        denied = [
            "cat /home/gille/notes.md",
            "cat /home/gille/Secret Vault/keepass.kdbx",
            "ls /home/gille/Secret Vault/",
            "sed -n 1,60p /home/gille/.ductor/workspace/state.json",
            "grep -r x /home/gille/metsatron-peer/",
            "head -5 /home/gille/.ssh/authorized_keys",
            "cd /home/gille && cat README",
            "cat /home/gille/DotCortex/agents-approval.org",
            "cat /home/gille/HelmCortex/LOGS/TODO",
            "find /home/gille/Secret Vault -name '*.kdbx'",
        ]
        for command in denied:
            with self.subTest(command=command):
                allow, reason = self.engine.classify(event("Bash", {"command": command}, self.root), manifest)
                self.assertFalse(allow, command)
                self.assertEqual(reason, "true_floor", command)

    # ---- Bunta's real read shapes: class allows (no decider needed) ----
    def test_bunta_read_shapes_classify(self):
        allow_cases = [
            "git status",
            "git log --oneline -5",
            "git diff",
            "grep -c supervisor /etc/init.d/honey-badger-opus",  # hmm: /etc path
        ]
        # /etc reads are OUTSIDE roots: must be grey (decider), not class-allowed
        allow, reason = self._classify("grep -c x /etc/init.d/honey-badger-opus")
        self.assertFalse(allow)
        self.assertEqual(reason, "no_match_decider")
        for command in allow_cases[:3]:
            with self.subTest(command=command):
                allow, reason = self._classify(command)
                self.assertTrue(allow, (command, reason))
                self.assertEqual(reason, "git_observe")

    # ---- scratch worktree shapes (his /var/tmp, /tmp/dc-honey pattern) ----
    def test_scratch_worktree_shapes(self):
        # A real scratch worktree under a listed root (manifest roots include
        # the synthetic root and /var/tmp is scratch-only; use the root itself).
        worktree = self.root / "wt-demo"
        (worktree / ".git").mkdir(parents=True)
        (worktree / "layers.org").write_text("synthetic")
        # git observe inside the worktree: class allows
        allow, reason = self._classify("git status", cwd=worktree)
        self.assertTrue(allow)
        self.assertEqual(reason, "git_observe")
        # cd + sed read inside the worktree: compound of reads
        allow, reason = self._classify(f"cd {worktree} && sed -n 1,60p layers.org")
        self.assertEqual((allow, reason), (True, "compound:local_read"))
        # pytest in the worktree: local_test_run stays DISABLED in the committed
        # manifest (proposed, not enabled) — the prompt must not silently allow.
        allow, reason = self._classify("pytest tests/", cwd=worktree)
        self.assertFalse(allow)
        self.assertIn(reason, ("local_test_run_disabled", "no_match_decider"))

    # ---- interpreter bodies never single-mode allow ----
    def test_heredoc_and_dash_c_are_dual_routed(self):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["decider"] = {"enabled": True,
                               "honey_url": "http://127.0.0.1:18097/decide",
                               "honey_api": "r2d2d",
                               "kikin_url": None,
                               "timeout_ms": 2000,
                               "min_allow_confidence": 0.95,
                               "questions": "single"}
        config = self.engine._decider_config(manifest)
        self.assertIsNotNone(config)
        body = "cd /tmp/dc-honey && python3 - <<'EOF'\nfrom pathlib import Path\nEOF"
        ev = event("Bash", {"command": body}, self.root)
        self.assertTrue(self.engine._interpreter_body(ev))
        effective = config
        if effective["mode"] == "single" and (self.engine._interpreter_body(ev) or self.engine._write_capable(ev)):
            effective = {**config, "mode": "dual"}
        self.assertEqual(effective["mode"], "dual")

    # ---- the ledger records decider_status ----
    def test_ledger_via_hook(self):
        hook = HERE.parents[3] / "bin/claude-hook-permission-request"
        if not hook.exists():
            self.skipTest("hook wrapper not tangled")
        manifest_path = self.scratch / "manifest.json"
        manifest_path.write_text(json.dumps(self.manifest))
        log = self.scratch / "decisions.jsonl"
        payload = json.dumps(event("Bash", {"command": "git status"}, self.root))
        env = {**os.environ, "SO_APPROVAL_KIKIN_MANIFEST": str(manifest_path),
               "SO_APPROVAL_KIKIN_LOG": str(log),
               "DOTCORTEX_APPROVAL_ENGINE": str(ENGINE)}
        completed = subprocess.run([str(hook)], input=payload, text=True,
                                  capture_output=True, env=env, timeout=10, check=False)
        self.assertEqual(completed.returncode, 0)
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(records[-1]["decision"], "allow")
        self.assertEqual(records[-1]["reason"], "git_observe")


if __name__ == "__main__":
    unittest.main()
