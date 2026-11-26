#!/usr/bin/env python3
"""Offline fixtures for Honey's Ductor voice engine (Badger and Flying Fox).

Every case runs in a throwaway HOME with a fake pvox client, a fake ffmpeg and,
for the send path, an in-process network sink: nothing reaches Telegram, no
real token is read, no live TTS engine renders.
"""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[5]
LANE = ROOT / "all/.local/share/dotcortex/honey-voice"
SPEAK = LANE / "bin/honey_speak.py"
HOOK = LANE / "bin/claude_stop_hook.py"
FOX = LANE / "bin/codex_rollout_watcher.py"
WATCHER = LANE / "bin/provider-rollout-watcher.py"
INSTALLER = LANE / "honey-voice-engine-install"
FIX = '[sys.executable, pvox, "render",'
DIRECT_EXEC = '[pvox, "render",'

FAKE_PVOX = '''#!/usr/bin/env python3
import sys, wave
args = sys.argv[1:]
assert args[0] == "render" and "--no-play" in args, args
with wave.open(args[-1], "wb") as out:
    out.setnchannels(1); out.setsampwidth(2); out.setframerate(16000)
    out.writeframes(b"\\0\\0" * 1600)
'''
FAKE_FFMPEG = '#!/bin/sh\nfor last; do :; done\nprintf OggS-fixture > "$last"\n'
SINK_DRIVER = '''
import io, json, runpy, sys, urllib.request
capture, script = sys.argv[1], sys.argv[2]
class Reply(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *exc): return False
def sink(request, timeout=None):
    with open(capture, "w") as f:
        json.dump({"url": request.full_url, "voice": b'name="voice"' in request.data,
                   "ogg": b"OggS-fixture" in request.data}, f)
    return Reply(json.dumps({"ok": True, "result": {"message_id": 7}}).encode())
urllib.request.urlopen = sink
sys.argv = [script] + sys.argv[3:]
runpy.run_path(script, run_name="__main__")
'''


def write(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)
    return path


class Home:
    """A throwaway account: voice engine, pvox client at 0644, fake ffmpeg."""

    def __init__(self, root, pvox_mode=0o644):
        self.home = root / "home"
        self.engine = self.home / ".local/share/honey-voice"
        self.pvox = write(self.home / ".local/share/pvox-clone/client/bin/pvox", FAKE_PVOX, pvox_mode)
        self.tools = root / "tools"
        write(self.tools / "ffmpeg", FAKE_FFMPEG, 0o755)
        self.ductor = root / "ductor"
        write(self.ductor / "config/config.json", json.dumps({"telegram_token": "fixture-token-not-real"}))
        voices = {bot: {"ductor_home": str(self.ductor), "provider": provider, "voice": "fixture",
                        "max_chars": None, "enabled": True}
                  for bot, provider in (("badger", "claude"), ("fox", "codex"))}
        write(self.engine / "voices.json", json.dumps(voices))
        self.log = self.home / ".local/state/honey-voice/voice.log"

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("HONEY_", "PYTHON"))}
        env.update(HOME=str(self.home), PATH="%s:%s" % (self.tools, env.get("PATH", "/usr/bin:/bin")))
        env.update(extra)
        return env

    def speak(self, script, *args):
        return subprocess.run([sys.executable, str(script), *args], env=self.env(),
                              capture_output=True, text=True, timeout=60)


class PvoxExecBitRegression(unittest.TestCase):
    """2026-11-19: the pvox client was reinstalled 0664 and direct exec failed."""

    def test_baseline_direct_exec_is_red_candidate_is_green(self):
        source = SPEAK.read_text()
        self.assertEqual(source.count(FIX), 1, "candidate must run the client through the interpreter")
        baselines = [("reverted", source.replace(FIX, DIRECT_EXEC))]
        if os.environ.get("HONEY_VOICE_BASELINE_SPEAK"):
            baselines.append(("external", Path(os.environ["HONEY_VOICE_BASELINE_SPEAK"]).read_text()))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = Home(root)
            self.assertFalse(os.access(home.pvox, os.X_OK))
            for name, text in baselines:
                baseline = write(root / ("baseline-%s.py" % name), text)
                done = home.speak(baseline, "--bot", "badger", "--text", "Baseline fixture.", "--no-send")
                self.assertEqual(done.returncode, 1, name)
                self.assertIn("badger FAIL PermissionError", home.log.read_text(), name)
            done = home.speak(SPEAK, "--bot", "badger", "--text", "Candidate fixture.", "--no-send")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue(Path(done.stdout.strip()).read_bytes().startswith(b"OggS-fixture"))
            self.assertRegex(home.log.read_text().splitlines()[-1],
                             r"badger RENDERED voice=pvox:HoneyBadger chars=\d+ dur=0\.1s \(no-send\)$")

    def test_send_path_reaches_only_the_sink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = Home(root)
            capture = root / "sink.json"
            done = subprocess.run([sys.executable, "-c", SINK_DRIVER, str(capture), str(SPEAK),
                                   "--bot", "fox", "--chat", "4242", "--text", "Sink fixture."],
                                  env=home.env(), capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)
            sent = json.loads(capture.read_text())
            self.assertTrue(sent["url"].endswith("/sendVoice"))
            self.assertTrue(sent["voice"] and sent["ogg"])
            log = home.log.read_text()
            self.assertIn("fox SENT chat=4242 message_id=7 voice=pvox:HoneyFlyingFox", log)
            self.assertNotIn("fixture-token-not-real", log)
            self.assertNotIn("Sink fixture", log)


class StopHookTests(unittest.TestCase):
    def run_hook(self, event):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        home = Home(root)
        record = root / "record.json"
        # The engine's renderer is a recorder at 0644: the hook must not need its execute bit.
        write(home.engine / "bin/honey_speak.py",
              "import json, sys\njson.dump(sys.argv[1:], open(%r, 'w'))\n" % str(record))
        done = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), env=home.env(),
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(done.returncode, 0)
        return record

    def test_stop_event_spawns_the_renderer_through_the_interpreter(self):
        record = self.run_hook({"hook_event_name": "Stop", "session_id": "fixture-session",
                                "last_assistant_message": "Hook fixture."})
        deadline = time.time() + 10
        while not record.exists() and time.time() < deadline:
            time.sleep(0.05)
        argv = json.loads(record.read_text())
        self.assertEqual(argv[:4], ["--bot", "badger", "--session", "fixture-session"])
        self.assertEqual(Path(argv[5]).read_text(), "Hook fixture.")

    def test_reentrant_stop_does_nothing(self):
        record = self.run_hook({"hook_event_name": "Stop", "stop_hook_active": True,
                                "session_id": "fixture-session", "last_assistant_message": "No."})
        time.sleep(1)
        self.assertFalse(record.exists())


class FoxEntrypointTests(unittest.TestCase):
    def load(self, path):
        spec = importlib.util.spec_from_file_location("fox_fixture", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_unit_environment_maps_to_the_watcher(self):
        fox = self.load(FOX)
        env = fox.configure({"HONEY_FOX_HOME": "/srv/fox", "HONEY_FOX_READ_AS": "foxagent"})
        self.assertEqual(env["HONEY_VOICE_BOT"], "fox")
        self.assertEqual(env["HONEY_VOICE_PROVIDER"], "codex")
        self.assertEqual(env["HONEY_VOICE_DUCTOR_HOME"], "/srv/fox/.ductor-codex")
        self.assertEqual(env["HONEY_VOICE_ROLLOUT_HOME"], "/srv/fox")
        self.assertEqual(env["HONEY_VOICE_READ_AS"], "foxagent")
        kept = fox.configure({"HONEY_FOX_HOME": "/srv/fox", "HONEY_VOICE_DUCTOR_HOME": "/srv/other"})
        self.assertEqual(kept["HONEY_VOICE_DUCTOR_HOME"], "/srv/other")
        self.assertNotIn("HONEY_VOICE_READ_AS", kept)
        with self.assertRaises(SystemExit):
            fox.configure({})

    def test_runs_the_hyphenated_watcher_without_a_second_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = Home(root)
            bin_dir = root / "engine-bin"
            for source in (FOX, WATCHER):
                write(bin_dir / source.name, source.read_text())
            self.assertFalse((bin_dir / "provider_rollout_watcher.py").exists())
            fox_home = root / "fox"
            (fox_home / ".ductor-codex").mkdir(parents=True)
            run = [sys.executable, str(bin_dir / FOX.name), "--once"]
            done = subprocess.run(run, env=home.env(HONEY_FOX_HOME=str(fox_home)),
                                  capture_output=True, text=True, timeout=20)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("fox watcher started provider=codex", done.stdout)
            done = subprocess.run(run, env=home.env(), capture_output=True, text=True, timeout=20)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("HONEY_FOX_HOME is not set", done.stderr)


class EngineInstallerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Home(Path(directory.name))

    def run_installer(self, *args):
        return subprocess.run(["bash", str(INSTALLER), *args], env=self.home.env(),
                              capture_output=True, text=True, timeout=30)

    def mode(self, name):
        return stat.S_IMODE((self.home.engine / name).stat().st_mode)

    def test_install_is_idempotent_and_sets_modes(self):
        dry = self.run_installer("--dry-run", "install")
        self.assertFalse((self.home.engine / "bin").exists(), dry.stdout)
        first = self.run_installer("install")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        for name in ("honey_speak.py", "claude_stop_hook.py", "codex_rollout_watcher.py",
                     "provider-rollout-watcher.py"):
            self.assertEqual((self.home.engine / "bin" / name).read_bytes(), (LANE / "bin" / name).read_bytes())
            self.assertEqual(self.mode("bin/" + name), 0o755)
        settings = json.loads((self.home.engine / "claude-settings.json").read_text())
        command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertEqual(command, "/usr/bin/python3 %s/bin/claude_stop_hook.py" % self.home.engine)
        self.assertEqual(self.mode("claude-settings.json"), 0o644)
        again = self.run_installer("check")
        self.assertEqual(again.returncode, 0, again.stdout)
        self.assertEqual(again.stdout.count("unchanged "), 5)
        self.assertNotIn("installed", self.run_installer("install").stdout)

    def test_check_reports_mode_and_content_drift_and_install_repairs(self):
        self.run_installer("install")
        (self.home.engine / "bin/honey_speak.py").chmod(0o644)
        with (self.home.engine / "bin/claude_stop_hook.py").open("a") as f:
            f.write("# drift\n")
        check = self.run_installer("check")
        self.assertEqual(check.returncode, 1)
        self.assertIn("!! mode 644 (want 755) %s/bin/honey_speak.py" % self.home.engine, check.stdout)
        self.assertIn("!! drift %s/bin/claude_stop_hook.py" % self.home.engine, check.stdout)
        fixed = self.run_installer("install")
        self.assertEqual(fixed.returncode, 0, fixed.stdout)
        self.assertEqual(self.mode("bin/honey_speak.py"), 0o755)
        backups = list((self.home.engine / "bin").glob("claude_stop_hook.py.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].read_text().endswith("# drift\n"))

    def test_pvox_execute_bit_is_warned_not_fatal(self):
        self.run_installer("install")
        check = self.run_installer("check")
        self.assertEqual(check.returncode, 0, check.stdout)
        self.assertIn("?? pvox client not executable (mode 644)", check.stdout)
        self.home.pvox.chmod(0o755)
        check = self.run_installer("check")
        self.assertIn("ok pvox client 755", check.stdout)
        self.assertNotIn("??", check.stdout)

    def test_machine_local_voices_json_is_required_but_never_written(self):
        (self.home.engine / "voices.json").unlink()
        done = self.run_installer("install")
        self.assertEqual(done.returncode, 1)
        self.assertIn("missing %s/voices.json" % self.home.engine, done.stdout)
        self.assertFalse((self.home.engine / "voices.json").exists())

    def test_legacy_watcher_copy_is_reported_only(self):
        self.run_installer("install")
        legacy = write(self.home.engine / "bin/provider_rollout_watcher.py", WATCHER.read_text())
        check = self.run_installer("check")
        self.assertIn("-- legacy %s" % legacy, check.stdout)
        self.assertTrue(legacy.exists())


class PrivacyTests(unittest.TestCase):
    def test_lane_payload_names_no_home_or_address(self):
        for path in [SPEAK, HOOK, FOX, INSTALLER, LANE / "claude-settings.json.template",
                     LANE / "voices.json.template"]:
            text = path.read_text()
            self.assertNotIn("/home/", text, path)
            self.assertNotRegex(text, r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", path)
            self.assertNotRegex(text, r"\d{6,}:[A-Za-z0-9_-]{30,}", path)


if __name__ == "__main__":
    unittest.main()
