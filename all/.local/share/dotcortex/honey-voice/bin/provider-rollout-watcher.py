#!/usr/bin/env python3
"""Provider-aware rollout watcher for Honey voice instances.

Each OpenRC instance supplies its own Ductor home, provider, rollout home,
state file, bot name, and optional chat allow-list.  A newly discovered
rollout is positioned at EOF, so startup never replays history.  Delivery
keys are persisted before spawning TTS, preventing duplicate voice notes after
an unclean watcher restart.
"""
import glob
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid


HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, ".local", "share", "honey-voice")
BOT = os.environ.get("HONEY_VOICE_BOT", "badger")
DUCTOR = os.environ.get("HONEY_VOICE_DUCTOR_HOME", os.path.join(HOME, ".ductor"))
PROVIDER = os.environ.get("HONEY_VOICE_PROVIDER", "codex")
ROLLOUT_HOME = os.environ.get("HONEY_VOICE_ROLLOUT_HOME", HOME)
READ_AS = os.environ.get("HONEY_VOICE_READ_AS", "")
STATE = os.environ.get("HONEY_VOICE_STATE", os.path.join(HOME, ".local", "state", "honey-voice"))
OFFSETS = os.path.join(STATE, "%s-offsets.json" % BOT)
PENDING = os.path.join(HOME, ".cache", "honey-voice", "pending")
DELIVERIES = os.path.join(STATE, "%s-deliveries.json" % BOT)
POLL_S = float(os.environ.get("HONEY_VOICE_POLL_SECONDS", "2"))
SESSIONS_GLOB = os.path.join(ROLLOUT_HOME, ".codex", "sessions", "**", "rollout-*%s.jsonl")


def say(msg):
    print("%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg), flush=True)


_threads_cache = {"mtime": None, "out": {}}


def read_text(path):
    try:
        with open(path) as f:
            return f.read()
    except PermissionError:
        if not READ_AS:
            raise
        done = subprocess.run(["sudo", "-n", "-u", READ_AS, "cat", "--", path],
                              capture_output=True, text=True, timeout=10)
        if done.returncode != 0:
            raise OSError("sudo cat failed")
        return done.stdout


def allowed_chat_ids():
    """Read the private Ductor allow-list; never put owner IDs in service source."""
    configured = os.environ.get("HONEY_VOICE_ALLOWED_CHAT_IDS", "")
    if configured:
        return {int(x) for x in configured.split(",") if x.strip().lstrip("-").isdigit()}
    try:
        data = json.loads(read_text(os.path.join(DUCTOR, "config", "config.json")))
        return {int(x) for x in data.get("allowed_user_ids", [])}
    except (OSError, ValueError, TypeError, KeyError):
        return set()


def threads():
    path = os.path.join(DUCTOR, "sessions.json")
    try:
        mtime = os.stat(path).st_mtime_ns
        if mtime == _threads_cache["mtime"]:
            return _threads_cache["out"]
        data = json.loads(read_text(path))
    except (OSError, ValueError, subprocess.SubprocessError):
        return _threads_cache.get("out", {})
    out = {}
    for entry in data.values():
        if entry.get("transport") != "tg":
            continue
        try:
            chat = int(entry["chat_id"])
        except (KeyError, TypeError, ValueError):
            continue
        allow = allowed_chat_ids()
        if allow and chat not in allow:
            continue
        provider_entry = (entry.get("provider_sessions") or {}).get(PROVIDER) or {}
        sid = provider_entry.get("session_id")
        if sid:
            out[str(sid)] = (chat, entry.get("topic_id"))
    _threads_cache.update(mtime=mtime, out=out)
    return out


def load_json(path):
    try:
        with open(path) as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_json(path, value):
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    tmp = path + ".tmp.%s" % uuid.uuid4().hex
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(value, f, separators=(",", ":"))
    os.replace(tmp, path)


def queue_voice(text, chat):
    os.makedirs(PENDING, mode=0o700, exist_ok=True)
    path = os.path.join(PENDING, "%s-%s.txt" % (BOT, uuid.uuid4().hex))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    subprocess.Popen([sys.executable, os.path.join(BASE, "bin", "honey_speak.py"),
                      "--bot", BOT, "--chat", str(chat), "--text-file", path],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)


def main():
    once = "--once" in sys.argv
    offsets = load_json(OFFSETS)
    deliveries = load_json(DELIVERIES)
    paths = {}
    say("%s watcher started provider=%s" % (BOT, PROVIDER))
    while True:
        changed = False
        for sid, (chat, _topic) in threads().items():
            path = paths.get(sid)
            if not path or not os.path.exists(path):
                found = sorted(glob.glob(SESSIONS_GLOB % sid, recursive=True), key=os.path.getmtime)
                if not found:
                    continue
                path = paths[sid] = found[-1]
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if path not in offsets or offsets[path] > size:
                offsets[path] = size
                changed = True
                say("following %s" % os.path.basename(path)[:60])
                continue
            if size == offsets[path]:
                continue
            start = offsets[path]
            with open(path, "rb") as f:
                f.seek(start)
                chunk = f.read(size - start)
            end = chunk.rfind(b"\n")
            if end < 0:
                continue
            for line in chunk[:end + 1].splitlines(keepends=True):
                line_start = start
                start += len(line)
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                payload = event.get("payload") or {}
                if event.get("type") != "event_msg" or not isinstance(payload, dict):
                    continue
                if payload.get("type") != "task_complete":
                    continue
                text = payload.get("last_agent_message") or ""
                if not text.strip():
                    continue
                key = hashlib.sha256((path + ":" + str(line_start)).encode()).hexdigest()
                if key in deliveries:
                    continue
                # Record before spawning: a restart cannot deliver this line twice.
                deliveries[key] = int(time.time())
                if len(deliveries) > 10000:
                    for old in sorted(deliveries, key=deliveries.get)[:2000]:
                        deliveries.pop(old, None)
                save_json(DELIVERIES, deliveries)
                queue_voice(text, chat)
                say("turn complete in %s -> voice queued (%d chars)" % (sid[:8], len(text)))
            offsets[path] = start
            changed = True
        if changed:
            save_json(OFFSETS, offsets)
        if once:
            return 0
        time.sleep(POLL_S)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
