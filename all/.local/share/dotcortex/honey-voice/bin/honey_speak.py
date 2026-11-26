#!/usr/bin/env python3
"""honey_speak.py — render a Ductor bot reply as a Telegram voice note (Honey, 2026-09-16).

Modeled on Aura's aura_voice.py (Hermes) but fully separate: own venv/voices under
~/.local/share/honey-voice, delivery straight to the Telegram Bot API (Ductor has no
post-response hook and uploads .ogg as a document, not a voice bubble).

  honey_speak.py --bot badger --session <id> --text-file <path>   (chat resolved from sessions.json, retries)
  honey_speak.py --bot fox --chat <id> --text-file <path>
  honey_speak.py --bot badger --text "..." --no-send               (render only; prints ogg path)
  honey_speak.py --sanitize < file                                   (debug the ear-text)

Config: ~/.local/share/honey-voice/voices.json  ("voice": null = wired but silent).
Token: read at runtime from <ductor_home>/config/config.json — never logged or copied.
Log: ~/.local/state/honey-voice/voice.log (0600, no reply text). Cache: ~/.cache/honey-voice (pruned >3d).
"""
import argparse, fcntl, json, os, re, subprocess, sys, time, uuid, urllib.request
import tempfile
import wave

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, ".local", "share", "honey-voice")
PY = os.path.join(BASE, "venv", "bin", "python")
VOICES = os.path.join(BASE, "voices")
CONF = os.path.join(BASE, "voices.json")
STATE = os.path.join(HOME, ".local", "state", "honey-voice")
LOG = os.path.join(STATE, "voice.log")
CACHE = os.path.join(HOME, ".cache", "honey-voice")
PRUNE_AGE_S = 3 * 86400


def log(msg):
    os.makedirs(STATE, mode=0o700, exist_ok=True)
    fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as f:
        f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))


def sanitize(text, max_chars=None):
    t = text
    t = re.sub(r"```.*?```", " (code omitted) ", t, flags=re.S)
    t = re.sub(r"\[button:[^\]]*\]", " ", t)
    t = re.sub(r"<file:[^>]*>", " (file attached) ", t)
    t = re.sub(r"\[([^\]]+)\]\((?:https?://)[^)]+\)", r"\1", t)
    t = re.sub(r"https?://\S+", " link ", t)
    lines = []
    for line in t.splitlines():
        s = line.strip()
        if s.startswith("|") or re.fullmatch(r"[-|: ]{3,}", s or "x"):
            continue                                  # tables
        if s.startswith("[Aura context]"):
            continue                                  # internal relay line
        s = re.sub(r"^#{1,6}\s*", "", s)              # headings
        s = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", s)  # bullets / numbering
        s = re.sub(r"^>\s?", "", s)                   # quotes
        lines.append(s)
    t = "\n".join(lines)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"(\*\*|__|\*|_|~~)(?=\S)(.+?)(?<=\S)\1", r"\2", t)
    t = re.sub(r"\s*→\s*", ", then ", t)
    t = t.replace(" & ", " and ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t).strip()
    if max_chars and len(t) > max_chars:            # no cap unless voices.json sets one (2026-10-07)
        cut = t[:max_chars]
        m = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("\n"))
        t = (cut[: m + 1] if m > max_chars * 0.5 else cut).rstrip() + " … The rest is in the chat."
    return t


def load_conf(bot):
    with open(CONF) as f:
        c = json.load(f)[bot]
    return c


def resolve_chat(conf, session_id, wait_s=25):
    """Map a provider session id to a Telegram chat via Ductor's sessions.json.
    Ductor records a NEW session id only after the CLI turn ends, so retry briefly."""
    path = os.path.join(conf["ductor_home"], "sessions.json")
    deadline = time.time() + wait_s
    while True:
        try:
            with open(path) as f:
                data = json.load(f)
            for entry in data.values():
                if entry.get("transport") != "tg":
                    continue
                ps = (entry.get("provider_sessions") or {}).get(conf["provider"]) or {}
                if ps.get("session_id") == session_id:
                    return int(entry["chat_id"]), entry.get("topic_id")
        except (OSError, ValueError, KeyError):
            pass
        if time.time() >= deadline:
            return None, None
        time.sleep(2)


def render_clone(text, agent):
    """Use the selected pvox profile; preserve the existing Telegram transport."""
    os.makedirs(CACHE, mode=0o700, exist_ok=True)
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONEXECUTABLE"):
        env.pop(key, None)
    pvox = os.path.join(HOME, ".local", "share", "pvox-clone", "client", "bin", "pvox")
    ogg = os.path.join(CACHE, "clone-" + uuid.uuid4().hex + ".ogg")
    with tempfile.TemporaryDirectory(prefix="clone-", dir=CACHE) as folder:
        source = os.path.join(folder, "text.txt")
        wav = os.path.join(folder, "speech.wav")
        with open(source, "w") as stream:
            stream.write(text)
        # Run the client through this interpreter: its execute bit is not part of the
        # contract.  A 2026-11-19 reinstall left it 0664 and every Badger and Flying Fox
        # voice note failed with PermissionError until 2026-11-26.
        subprocess.run([sys.executable, pvox, "render", "--agent", agent, "--no-play", source, wav],
                       check=True, capture_output=True, timeout=1800, env=env)
        with wave.open(wav) as audio:
            duration = audio.getnframes() / audio.getframerate()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                        "-c:a", "libopus", "-b:a", "32k", ogg],
                       check=True, capture_output=True, timeout=120, env=env)
    os.chmod(ogg, 0o600)
    return ogg, duration


def render(text, voice, pvox_agent=None):
    if pvox_agent:
        return render_clone(text, pvox_agent)
    onnx = os.path.join(VOICES, voice + ".onnx")
    with open(onnx + ".json") as f:
        rate = int(json.load(f)["audio"]["sample_rate"])
    os.makedirs(CACHE, mode=0o700, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    ogg = os.path.join(CACHE, "%s.ogg" % stamp)
    piper = subprocess.run([PY, "-m", "piper", "-m", onnx, "--output-raw"], input=text.encode(),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180 + len(text) // 20)
    if piper.returncode != 0 or not piper.stdout:
        raise RuntimeError("piper failed rc=%s %s" % (piper.returncode, piper.stderr[-200:]))
    ff = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(rate), "-ac", "1",
                         "-i", "-", "-c:a", "libopus", "-b:a", "32k", ogg],
                        input=piper.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120 + len(text) // 40)
    if ff.returncode != 0 or not os.path.exists(ogg):
        raise RuntimeError("ffmpeg failed rc=%s %s" % (ff.returncode, ff.stderr[-200:]))
    os.chmod(ogg, 0o600)
    return ogg, len(piper.stdout) / 2 / rate


def send_voice(token, chat_id, ogg, duration, topic_id=None, caption=None):
    boundary = "----honeyvoice" + uuid.uuid4().hex
    parts = []
    def field(name, value):
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, name, value)).encode())
    field("chat_id", str(chat_id))
    field("duration", str(int(round(duration))))
    if topic_id:
        field("message_thread_id", str(topic_id))
    if caption:
        field("caption", caption[:1000])
    with open(ogg, "rb") as f:
        audio = f.read()
    parts.append(("--%s\r\nContent-Disposition: form-data; name=\"voice\"; filename=\"voice.ogg\"\r\nContent-Type: audio/ogg\r\n\r\n" % boundary).encode())
    parts.append(audio + b"\r\n")
    parts.append(("--%s--\r\n" % boundary).encode())
    req = urllib.request.Request("https://api.telegram.org/bot%s/sendVoice" % token, data=b"".join(parts),
                                 headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary})
    with urllib.request.urlopen(req, timeout=60 + len(audio) // 20000) as r:
        body = json.load(r)
    if not body.get("ok"):
        raise RuntimeError("telegram not ok: %s" % str(body)[:200])
    return body


def prune():
    now = time.time()
    for root in (CACHE, os.path.join(CACHE, "pending")):
        try:
            for name in os.listdir(root):
                p = os.path.join(root, name)
                if os.path.isfile(p) and now - os.path.getmtime(p) > PRUNE_AGE_S:
                    os.unlink(p)
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot", choices=["badger", "fox"])
    ap.add_argument("--session")
    ap.add_argument("--chat", type=int)
    ap.add_argument("--text-file")
    ap.add_argument("--text")
    ap.add_argument("--voice")
    ap.add_argument("--caption")
    ap.add_argument("--no-send", action="store_true")
    ap.add_argument("--sanitize", action="store_true")
    a = ap.parse_args()
    if a.sanitize:
        print(sanitize(sys.stdin.read()))
        return 0
    conf = load_conf(a.bot)
    raw = a.text if a.text is not None else open(a.text_file).read()
    if a.text_file and not a.no_send:
        try:
            os.unlink(a.text_file)            # pending reply text never lingers on disk
        except OSError:
            pass
    voice = a.voice or conf.get("voice")
    pvox_agent = None if a.voice else {"badger": "HoneyBadger", "fox": "HoneyFlyingFox"}.get(a.bot)
    voice_label = "pvox:" + pvox_agent if pvox_agent else voice
    if not conf.get("enabled", True):
        return 0
    if not voice:
        log("%s SKIP no voice chosen" % a.bot)
        return 0
    text = sanitize(raw, conf.get("max_chars"))
    if len(text) < 2:
        log("%s SKIP empty after sanitize" % a.bot)
        return 0
    os.makedirs(STATE, mode=0o700, exist_ok=True)
    lock = open(os.path.join(STATE, "%s.lock" % a.bot), "w")
    fcntl.flock(lock, fcntl.LOCK_EX)          # one voice at a time per bot, in order
    try:
        chat, topic = a.chat, None
        if not a.no_send and chat is None:
            chat, topic = resolve_chat(conf, a.session)
            if chat is None:
                log("%s SKIP session %s not a Telegram session" % (a.bot, (a.session or "")[:8]))
                return 0
        ogg, dur = render(text, voice, pvox_agent=pvox_agent)
        if a.no_send:
            print(ogg)
            log("%s RENDERED voice=%s chars=%d dur=%.1fs (no-send)" % (a.bot, voice_label, len(text), dur))
            return 0
        cfg = os.path.join(conf["ductor_home"], "config", "config.json")
        try:
            with open(cfg) as f:
                token = json.load(f)["telegram_token"]
        except PermissionError:               # 2026-09-25: fox's home is agent-codex's (see voices.json read_as)
            if not conf.get("read_as"):
                raise
            done = subprocess.run(["sudo", "-n", "-u", conf["read_as"], "cat", "--", cfg],
                                  capture_output=True, text=True, timeout=10, check=True)
            token = json.loads(done.stdout)["telegram_token"]
        result = send_voice(token, chat, ogg, dur, topic, a.caption)
        message_id = ((result.get("result") or {}).get("message_id")) if isinstance(result, dict) else None
        log("%s SENT chat=%s message_id=%s voice=%s chars=%d dur=%.1fs" %
            (a.bot, chat, message_id if message_id is not None else "unknown", voice_label, len(text), dur))
    except Exception as e:                    # never raise into a hook
        log("%s FAIL %s: %s" % (a.bot, type(e).__name__, str(e)[:200].replace(conf.get("ductor_home", ""), "~")))
        return 1
    finally:
        prune()
    return 0


if __name__ == "__main__":
    sys.exit(main())
