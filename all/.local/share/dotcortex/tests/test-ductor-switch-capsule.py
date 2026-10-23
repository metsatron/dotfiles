"""Switch-capsule seam: marker logic, fail-open paths, applier and patched _route_message."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from types import SimpleNamespace
import unittest

SEAMS = Path(__file__).resolve().parents[1] / "ductor-seams"
APPLIER = SEAMS.parents[2] / "bin/ductor-seam-apply"
_spec = importlib.util.spec_from_file_location("ductor_switch_capsule_seam", SEAMS / "switch_capsule.py")
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

KEY = SimpleNamespace(storage_key="tg:111")
CAPSULE_LINES = [f"line {i:03d} " + "x" * 40 for i in range(120)]


def make_home(root: Path, name="ductor", recorded="claude", capsule=True):
    home = root / name
    (home / "workspace/memory_system").mkdir(parents=True)
    (home / "config").mkdir()
    (home / "sessions.json").write_text(json.dumps({KEY.storage_key: {"provider": recorded}}))
    if capsule:
        (home / "workspace/memory_system/SWITCH_CAPSULE.md").write_text("\n".join(CAPSULE_LINES) + "\n")
    return home


def orch(home, provider):
    return SimpleNamespace(paths=SimpleNamespace(ductor_home=home), _config=SimpleNamespace(provider=provider))


class MarkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_claude_to_codex_switch_then_untouched(self):
        home = make_home(self.root, recorded="claude")
        first = sc.with_capsule(orch(home, "codex"), KEY, "hello")
        self.assertTrue(first.startswith("[SWITCH CAPSULE: this chat was just switched from claude to codex."))
        self.assertTrue(first.endswith("[END SWITCH CAPSULE]\n\nhello"))
        head = first.split("]\n", 1)[1].split("[END SWITCH CAPSULE]")[0]
        self.assertLessEqual(len(head.encode()), 2048 + 1)
        self.assertTrue(head.rstrip().split("\n")[-1].startswith("line "))
        self.assertIn("line 000", head)
        self.assertNotIn("line 119", head)
        marker = json.loads((home / "switch_capsule_seen.json").read_text())
        self.assertEqual(marker[KEY.storage_key]["provider"], "codex")
        self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "second"), "second")
        self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "third"), "third")
        back = sc.with_capsule(orch(home, "claude"), KEY, "back")
        self.assertIn("switched from codex to claude", back)
        self.assertEqual(sc.with_capsule(orch(home, "claude"), KEY, "again"), "again")

    def test_no_switch_initialises_marker_only(self):
        home = make_home(self.root, recorded="codex")
        self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "m"), "m")
        self.assertEqual(json.loads((home / "switch_capsule_seen.json").read_text())[KEY.storage_key]["provider"], "codex")

    def test_no_marker_no_record_never_injects(self):
        home = make_home(self.root)
        (home / "sessions.json").unlink()
        self.assertEqual(sc.with_capsule(orch(home, "claude"), KEY, "m"), "m")

    def test_both_home_layouts(self):
        for name in ("ductor", "agent-codex/.ductor-codex"):
            with self.subTest(home=name):
                home = make_home(self.root, name=name, recorded="claude")
                self.assertIn("SWITCH CAPSULE", sc.with_capsule(orch(home, "codex"), KEY, "m"))

    def test_codex_only_home_without_capsule_is_noop(self):
        home = make_home(self.root, name="agent-codex/.ductor-codex", recorded="codex", capsule=False)
        for _ in range(3):
            self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "m"), "m")

    def test_missing_capsule_fails_open_and_keeps_marker_for_retry(self):
        home = make_home(self.root, recorded="claude", capsule=False)
        self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "m"), "m")
        self.assertFalse((home / "switch_capsule_seen.json").exists())
        (home / "workspace/memory_system/SWITCH_CAPSULE.md").write_text("later\n")
        self.assertIn("later", sc.with_capsule(orch(home, "codex"), KEY, "m"))

    def test_empty_capsule_is_ignored(self):
        home = make_home(self.root, recorded="claude")
        (home / "workspace/memory_system/SWITCH_CAPSULE.md").write_text("\n  \n")
        self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "m"), "m")

    def test_unwritable_marker_fails_open(self):
        if os.geteuid() == 0:
            self.skipTest("root ignores directory modes")
        home = make_home(self.root, recorded="claude")
        home.chmod(0o500)
        self.addCleanup(home.chmod, 0o700)
        self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "m"), "m")

    def test_unreadable_capsule_fails_open(self):
        if os.geteuid() == 0:
            self.skipTest("root ignores file modes")
        home = make_home(self.root, recorded="claude")
        (home / "workspace/memory_system/SWITCH_CAPSULE.md").chmod(0)
        self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "m"), "m")

    def test_garbage_state_and_broken_orchestrator_fail_open(self):
        home = make_home(self.root, recorded="claude")
        (home / "switch_capsule_seen.json").write_text("{not json")
        (home / "sessions.json").write_text("[1, 2")
        self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "m"), "m")
        self.assertEqual(sc.with_capsule(SimpleNamespace(), KEY, "m"), "m")
        self.assertEqual(sc.with_capsule(orch(home, None), SimpleNamespace(), "m"), "m")

    def test_disabled_and_settings(self):
        home = make_home(self.root, recorded="claude")
        (home / "config/config.json").write_text(json.dumps({"switch_capsule": {"enabled": False}}))
        self.assertEqual(sc.with_capsule(orch(home, "codex"), KEY, "m"), "m")
        (home / "config/config.json").write_text(json.dumps({"switch_capsule": {"head_bytes": 200}}))
        out = sc.with_capsule(orch(home, "codex"), KEY, "m")
        head = out.split("]\n", 1)[1].split("[END SWITCH CAPSULE]")[0]
        self.assertLessEqual(len(head.encode()), 201)
        self.assertIn("line 000", head)

    def test_stale_capsule_is_labelled(self):
        home = make_home(self.root, recorded="claude")
        cap = home / "workspace/memory_system/SWITCH_CAPSULE.md"
        old = time.time() - 3 * 3600
        os.utime(cap, (old, old))
        self.assertIn("STALE: 180 min old", sc.with_capsule(orch(home, "codex"), KEY, "m"))


SCRIPT = textwrap.dedent("""
    import asyncio, json, sys
    from pathlib import Path
    from types import SimpleNamespace
    from unittest import mock
    from ductor_bot.orchestrator import core
    from ductor_bot.session.key import SessionKey

    home = Path(sys.argv[1])
    key = SessionKey(transport="tg", chat_id=111, topic_id=None)
    seen = []

    async def fake_stream(orch, k, prompt, **kw):
        seen.append(prompt)
        return "ok"

    async def none(*a, **kw):
        return None

    def fake(provider):
        o = SimpleNamespace()
        o._command_registry = SimpleNamespace(dispatch=none)
        o._ensure_docker = none
        o._providers = SimpleNamespace(_known_model_ids=frozenset(), _codex_cache_fn=None)
        o._named_sessions = SimpleNamespace(get=lambda *a: None)
        o.paths = SimpleNamespace(ductor_home=home)
        o._config = SimpleNamespace(provider=provider)
        return o

    async def send(provider, text):
        d = core._MessageDispatch(key=key, text=text, cmd=text.strip().lower(), streaming=True)
        return await core.Orchestrator._route_message(fake(provider), d)

    async def main():
        with mock.patch.object(core, "normal_streaming", fake_stream):
            await send("claude", "m0")
            await send("codex", "m1")
            await send("codex", "m2")
            (home / "workspace/memory_system/SWITCH_CAPSULE.md").unlink()
            await send("claude", "m3")          # switch but no capsule: unchanged, still delivered
            (home / "workspace/memory_system/SWITCH_CAPSULE.md").write_text("capsule body\\n")
            await send("claude", "m4")          # retry succeeds
    asyncio.run(main())
    print(json.dumps(seen))
""")


class AppliedSeamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.find_spec("ductor_bot")
        if spec is None or not spec.submodule_search_locations:
            raise unittest.SkipTest("ductor_bot not installed")
        cls.installed = Path(list(spec.submodule_search_locations)[0])
        cls.tmp = tempfile.TemporaryDirectory(prefix="ductor-capsule-test-")
        cls.site = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def snapshot(root):
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}

    def fresh_site(self, root):
        site = Path(root)
        shutil.copytree(self.installed, site / "ductor_bot", ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("switch_capsule_core.patch",):  # a live package may already carry the seam
            command = ["patch", "-d", str(site), "-p1", "--fuzz=0", "--reverse", "--force", "-s"]
            patch = (SEAMS / name).read_bytes()
            if subprocess.run(command + ["--dry-run"], input=patch, capture_output=True).returncode == 0:
                subprocess.run(command, input=patch, capture_output=True, check=True)
        (site / "ductor_bot/orchestrator/switch_capsule.py").unlink(missing_ok=True)
        return site

    def apply(self, site, *args):
        env = dict(os.environ, DOTCORTEX_DUCTOR_SEAMS=str(SEAMS), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(["bash", str(APPLIER), "--site", str(site), *args], env=env, text=True,
                              capture_output=True)

    def test_apply_check_idempotence_and_end_to_end(self):
        site = self.fresh_site(self.tmp.name + "/a") if (Path(self.tmp.name) / "a").mkdir() is None else None
        pending = self.apply(site, "--check")
        self.assertEqual(pending.returncode, 1, pending.stdout + pending.stderr)
        self.assertIn("switch_capsule: module=missing hook=missing", pending.stdout)
        done = self.apply(site)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        core_src = (site / "ductor_bot/orchestrator/core.py").read_text()
        self.assertEqual(core_src.count("with_capsule(self, dispatch.key, prompt_text)"), 1)
        self.assertTrue((site / "ductor_bot/orchestrator/switch_capsule.py").is_file())
        before = self.snapshot(site)
        again = self.apply(site)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn("already applied", again.stdout)
        self.assertEqual(self.snapshot(site), before)
        self.assertEqual(self.apply(site, "--check").returncode, 0)
        # end to end through the patched _route_message
        with tempfile.TemporaryDirectory() as root:
            home = make_home(Path(root), recorded="claude")
            result = subprocess.run(
                [sys.executable, "-c", SCRIPT, str(home)], cwd="/tmp", text=True, capture_output=True,
                env=dict(os.environ, PYTHONPATH=str(site), PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            seen = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(seen[0], "m0")                       # no switch yet
        self.assertIn("switched from claude to codex", seen[1])
        self.assertTrue(seen[1].endswith("\n\nm1"))
        self.assertEqual(seen[2], "m2")                       # subsequent message untouched
        self.assertEqual(seen[3], "m3")                       # capsule missing: fail open
        self.assertIn("capsule body", seen[4])                # retry delivers it
        self.assertTrue(seen[4].endswith("\n\nm4"))

    def test_fail_open_when_seam_module_is_broken_or_missing(self):
        with tempfile.TemporaryDirectory() as root:
            site = self.fresh_site(root + "/s") if (Path(root) / "s").mkdir() is None else None
            self.assertEqual(self.apply(site).returncode, 0)
            module = site / "ductor_bot/orchestrator/switch_capsule.py"
            home_root = Path(root) / "h"
            home_root.mkdir()
            home = make_home(home_root, recorded="claude")
            for mutate in (lambda: module.write_text("raise RuntimeError('boom')\n"), module.unlink):
                mutate()
                result = subprocess.run(
                    [sys.executable, "-c", SCRIPT, str(home)], cwd="/tmp", text=True, capture_output=True,
                    env=dict(os.environ, PYTHONPATH=str(site), PYTHONDONTWRITEBYTECODE="1"))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1]),
                                 ["m0", "m1", "m2", "m3", "m4"])

    def test_drift_refuses_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as root:
            site = self.fresh_site(root + "/d") if (Path(root) / "d").mkdir() is None else None
            target = site / "ductor_bot/orchestrator/core.py"
            source = target.read_text()
            needle = "        prompt_text = directives.cleaned or dispatch.text\n"
            self.assertEqual(source.count(needle), 1)
            target.write_text(source.replace(needle, needle + "        # upstream drift\n"))
            before = self.snapshot(site)
            for args in ((), ("--check",)):
                result = self.apply(site, *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("switch_capsule: orchestrator/core.py drifted", result.stderr)
                self.assertEqual(self.snapshot(site), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
