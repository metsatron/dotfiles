#!/usr/bin/env python3
"""claude_stop_hook.py — Honey Badger voice hook (Claude Code Stop event, Honey 2026-09-16).
Loaded ONLY for Honey Badger's own CLI via `--settings ~/.local/share/honey-voice/claude-settings.json`
in ~/.ductor/config/config.json cli_parameters.claude. Hands the reply to honey_speak.py in a
detached process and exits at once, so the turn is never delayed. Non-Telegram sessions
(background tasks, cron) are filtered by honey_speak.py's sessions.json lookup."""
import json, os, subprocess, sys, uuid

BASE = os.path.expanduser("~/.local/share/honey-voice")
PENDING = os.path.expanduser("~/.cache/honey-voice/pending")

def main():
    try:
        d = json.load(sys.stdin)
        if d.get("hook_event_name") != "Stop" or d.get("stop_hook_active"):
            return
        text = d.get("last_assistant_message") or ""
        sid = d.get("session_id") or ""
        if not text.strip() or not sid:
            return
        os.makedirs(PENDING, mode=0o700, exist_ok=True)
        path = os.path.join(PENDING, "badger-%s.txt" % uuid.uuid4().hex)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(text)
        subprocess.Popen([sys.executable, os.path.join(BASE, "bin", "honey_speak.py"),
                          "--bot", "badger", "--session", sid, "--text-file", path],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)
    except Exception:
        pass  # a voice problem must never break a reply

if __name__ == "__main__":
    main()
    sys.exit(0)
