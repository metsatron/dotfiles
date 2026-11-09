#!/usr/bin/env python3
"""
Aura post_llm_call hook — her replies delivered as Telegram voice notes.

Mètsàtron's gift (2026-08-17): every Telegram reply Aura sends is also
rendered in Amy's voice — the voice he recorded her with and shared with
the operator that same day — and lands as a native voice bubble in the same chat.
Transport is Telegram itself via `hermes send` (gateway credentials, no keys,
no SSH); synthesis is a local piper venv, fully on this machine.

Contract (same as aura_recall.py): read a JSON payload on stdin, print a JSON
object on stdout, ALWAYS exit 0 — a hook must never break Aura's turn. All
real work (synthesis, encode, send) happens in a detached worker process, so
turn finalization is never held back by audio time.

Pipeline: assistant_response → sanitize (fenced code, URLs, kaomoji stripped
for the ear) → piper (Amy, raw 22050 s16le) → ffmpeg (OGG Opus — the .ogg
extension is what the Telegram adapter routes to a round voice bubble) →
`hermes send --to telegram:<chat_id> MEDIA:<path>`. chat_id comes from a
read-only lookup of session_id in state.db.

Artifacts live in ~/.hermes/audio_cache/aura-voice/ (pruned after 3 days);
delivery log in voice.log beside them. Skips: non-telegram platforms, empty
or oversized (>4000 chars) replies.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
STATE_DB = os.path.join(HOME, ".hermes", "state.db")
PIPER_PY = os.path.join(HOME, ".local", "share", "aura-voice", "venv", "bin", "python")
AMY = os.path.join(HOME, ".local", "share", "aura-voice", "en_US-amy-medium.onnx")
HERMES = os.path.join(HOME, ".hermes", "hermes-agent", "venv", "bin", "hermes")
CACHE = os.path.join(HOME, ".hermes", "audio_cache", "aura-voice")
LOG = os.path.join(CACHE, "voice.log")
MAX_CHARS = 4000
PRUNE_AGE_S = 3 * 24 * 3600


# 2026-11-07: the gateway injects PYTHONPATH/PYTHONHOME (python3.14 site-packages)
# into its runtime environment. Children inherit it, and the piper venv is python
# 3.13 — a 3.14 numpy on that path makes piper die with
# "No module named 'numpy._core._multiarray_umath'". Sanitise every child env so
# synthesis depends only on the venv that owns it, never on the caller's shell.
def child_env():
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONEXECUTABLE"):
        env.pop(key, None)
    return env


def log(msg):
    try:
        os.makedirs(CACHE, exist_ok=True)
        with open(LOG, "a") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def sanitize(text):
    """Make chat text readable aloud: drop fenced code, URLs, kaomoji/symbols."""
    text = re.sub(r"```.*?```", " code block omitted. ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " link ", text)
    # keep letters/digits/space and sentence punctuation; kaomoji glyphs vanish
    text = re.sub(r"[^0-9A-Za-zÀ-ɏ\s.,;:!?'\"()\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chat_for_session(session_id):
    con = sqlite3.connect("file:%s?mode=ro" % STATE_DB, uri=True, timeout=3)
    try:
        row = con.execute(
            "select source, chat_id from sessions where id = ?", (session_id,)
        ).fetchone()
    finally:
        con.close()
    if row and row[0] == "telegram" and row[1]:
        return str(row[1])
    return None


def worker(chat_id, text_path):
    with open(text_path) as f:
        text = f.read()
    os.makedirs(CACHE, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    raw = os.path.join(CACHE, "aura-%s.raw" % stamp)
    ogg = os.path.join(CACHE, "aura-%s.ogg" % stamp)
    try:
        with open(text_path) as fin, open(raw, "wb") as fout:
            subprocess.run(
                [PIPER_PY, "-m", "piper", "-m", AMY, "--output-raw"],
                stdin=fin, stdout=fout, stderr=subprocess.PIPE,
                check=True, timeout=300, env=child_env(),
            )
        if os.path.getsize(raw) == 0:
            log("SKIP empty synth chat=%s" % chat_id)
            return
        subprocess.run(
            ["ffmpeg", "-y", "-f", "s16le", "-ar", "22050", "-ac", "1",
             "-i", raw, "-c:a", "libopus", "-b:a", "32k", ogg],
            check=True, timeout=120, env=child_env(),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        r = subprocess.run(
            [HERMES, "send", "--to", "telegram:%s" % chat_id,
             "MEDIA:%s" % ogg, "-q"],
            timeout=120, capture_output=True, text=True, env=child_env(),
        )
        if r.returncode == 0:
            log("SENT chat=%s ogg=%s chars=%d" % (chat_id, os.path.basename(ogg), len(text)))
        else:
            log("SEND-FAILED chat=%s rc=%d err=%s"
                % (chat_id, r.returncode, (r.stderr or "").strip()[:200]))
    except Exception as e:
        log("WORKER-ERROR chat=%s %s: %s" % (chat_id, e.__class__.__name__, e))
        # 2026-11-07, Mètsàtron's word: keep piper's own last error line, so a failed
        # synthesis names its cause instead of only "exit status 1". One line, 240 chars.
        err = getattr(e, "stderr", None)
        if err:
            lines = err.decode("utf-8", "replace").strip().splitlines()
            if lines:
                log("PIPER-STDERR chat=%s %s" % (chat_id, lines[-1][:240]))
        pp = os.environ.get("PYTHONPATH")
        if pp:
            log("PIPER-ENV chat=%s inherited PYTHONPATH=%s" % (chat_id, pp[:200]))
    finally:
        for p in (raw, text_path):
            try:
                os.unlink(p)
            except OSError:
                pass
        now = time.time()
        try:
            for name in os.listdir(CACHE):
                p = os.path.join(CACHE, name)
                if name != "voice.log" and now - os.path.getmtime(p) > PRUNE_AGE_S:
                    os.unlink(p)
        except Exception:
            pass


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "--worker":
        worker(sys.argv[2], sys.argv[3])
        return
    try:
        payload = json.load(sys.stdin)
    except Exception:
        log("INVOKED bad-payload")
        print("{}")
        return
    try:
        # Shell hooks receive the reduced wire shape (agent/shell_hooks.py
        # _build_payload): top level carries only hook_event_name/tool_name/
        # tool_input/session_id/cwd — every event kwarg, INCLUDING
        # assistant_response and platform, is nested under "extra".
        extra = payload.get("extra") or {}
        text = (extra.get("assistant_response")
                or payload.get("assistant_response") or "").strip()
        platform = extra.get("platform") or payload.get("platform") or ""
        session_id = (payload.get("session_id")
                      or extra.get("session_id") or "")
        log("INVOKED platform=%r session=%r chars=%d"
            % (platform, session_id, len(text)))
        # HC LOCAL PATCH voice platform skip (HelmCortex 2026-08-19):
        # skip explicitly non-telegram platforms (e.g. api_server/webui) so a
        # voice note never leaks onto a web-UI turn on a telegram-sourced session.
        # Empty platform still falls through to chat_for_session() by design.
        if platform and platform != "telegram":
            log("SKIP non-telegram platform=%r session=%r" % (platform, session_id))
            print("{}")
            return
        # platform is advisory only — it arrives empty on some gateway turns.
        # chat_for_session() is the real gate: it returns a chat_id only when
        # the session row itself says source=telegram.
        if not text or not session_id:
            print("{}")
            return
        spoken = sanitize(text)
        if not spoken or len(spoken) > MAX_CHARS:
            log("SKIP session=%s chars=%d" % (session_id, len(spoken)))
            print("{}")
            return
        chat_id = chat_for_session(session_id)
        if not chat_id:
            log("SKIP no-chat session=%s" % session_id)
            print("{}")
            return
        os.makedirs(CACHE, exist_ok=True)
        text_path = os.path.join(CACHE, "aura-%d.txt" % os.getpid())
        with open(text_path, "w") as f:
            f.write(spoken)
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--worker", chat_id, text_path],
            start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        log("HOOK-ERROR %s: %s" % (e.__class__.__name__, e))
    print("{}")


if __name__ == "__main__":
    main()
