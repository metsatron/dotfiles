#!/usr/bin/env python3
"""
Aura pre_llm_call hook.

Fires once per turn (after context compression, before the tool loop). Injects,
into the current turn's user message:
  1. an identity + interlocutor anchor  — cheap, always (re-grounds Aura after a
     compaction, and tells her which of her people she's talking to)
  2. top-k semantic recall from the Odysseus RAG for the user's message — via
     `docker exec` into the odysseus container, best-effort with a hard timeout.

Contract: read a JSON payload on stdin, print a JSON object on stdout. Return
{"context": "..."} to inject, or {} for no-op. Any error / timeout must still
print valid JSON and exit 0 — a hook must never break Aura's turn.
"""
import json
import os
import subprocess
import sys

STATE_DB = "/home/gille/.hermes/state.db"
CONTAINER = "odysseus-odysseus-1"
RECALL_K = 3
RECALL_MIN_SIM = 0.45        # recalibrated 0.50 -> 0.45 on 2026-08-25 (Claudeificus + Mètsàtron): a live probe found genuine conversational memories at 0.48-0.58, BELOW the 0.57-0.76 the 0.50 floor assumed, so 0.50 was clipping real memories (one cut at 0.489). 0.45 clears the 0.38-0.44 low-signal band noted below while recovering them. Clinical stays safe: the RAG indexes only aura_conversations + the Obsidian Vault, NEVER the Secret Vault. Instant rollback: .bak-2026-08-25-floorcal.
# Floor raised 0.2 -> 0.5 on 2026-08-10 after a live probe: genuine hits sit at
# 0.57-0.76 across clinical/technical/personal registers, while low-signal turns
# (e.g. "what were we working on") collapse to 0.38-0.44 noise that the old 0.2
# floor still injected. 0.5 cuts the clean gap: vague turns now inject nothing
# (better than wrong-register memories) while every real hit survives.
RECALL_TIMEOUT = 6            # seconds for the docker exec search
SNIPPET_CHARS = 220

# Telegram chat_id -> how Aura should think of that person.
PEOPLE = {
    "1973228690": "the operator (Gill) — Melbourne OT, your art collaborator",
    "111081877": "Mètsàtron (Tiago) — builder/operator of this stack",
}


def _emit(obj):
    sys.stdout.write(json.dumps(obj))
    sys.stdout.flush()


def _interlocutor(session_id, platform):
    """Best-effort: who is Aura talking to this turn?"""
    if not session_id:
        return None
    try:
        import sqlite3
        con = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True, timeout=2)
        row = con.execute(
            "SELECT chat_id, display_name, source FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        con.close()
    except Exception:
        return None
    if not row:
        return None
    chat_id, display_name, source = row
    if chat_id and str(chat_id) in PEOPLE:
        return PEOPLE[str(chat_id)]
    if display_name:
        return f"{display_name} (via {platform or source or 'unknown'})"
    return None


def _recall(query):
    """Top-k RAG hits for `query`, via the odysseus container. Never raises."""
    query = (query or "").strip()
    if len(query) < 4:
        return []
    # Over-fetch (k*3) so hook-side junk filtering still leaves good hits.
    snippet = (
        "import sys,os,json;sys.path.insert(0,'/app');"
        "from src.rag_singleton import get_rag_manager;"
        "q=os.environ.get('AURA_Q','');"
        "res=[];\n"
        "try:\n res=get_rag_manager().search(q,%d)\nexcept Exception:\n res=[]\n"
        "out=[]\n"
        "for r in res:\n"
        " m=r.get('metadata') or {}\n"
        " out.append({'src':(m.get('source') or ''),"
        "'sim':r.get('similarity'),"
        "'snip':' '.join((r.get('document') or '').split())[:%d]})\n"
        "print(json.dumps(out))" % (RECALL_K * 3, SNIPPET_CHARS)
    )
    try:
        proc = subprocess.run(
            ["docker", "exec", "-e", "AURA_Q", "-i", CONTAINER, "python", "-c", snippet],
            input="",
            env={**os.environ, "AURA_Q": query},
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=RECALL_TIMEOUT,
            text=True,
        )
    except Exception:
        return []
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    try:
        hits = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return []
    out = []
    seen = set()
    for h in hits:
        sim = h.get("sim")
        if sim is not None and sim < RECALL_MIN_SIM:
            continue
        if not _is_useful_hit(h):
            continue
        # Drop exact-duplicate chunks so identical text doesn't eat the k budget.
        key = " ".join((h.get("snip") or "").split()).lower()
        if key in seen:
            continue
        seen.add(key)
        h["name"] = (h.get("src") or "").split("/")[-1]
        out.append(h)
        if len(out) >= RECALL_K:
            break
    return out


# Sources that are indexed but never useful to recall into Aura's context.
_JUNK_PATH_MARKERS = ("/.obsidian/", "/node_modules/", "/.git/")
_JUNK_EXTS = (".js", ".css", ".map", ".mjs", ".min.js", ".lock", ".json")


def _is_useful_hit(h):
    """Drop plugin/build junk and binary-looking snippets (e.g. minified JS)."""
    src = (h.get("src") or "").lower()
    if any(marker in src for marker in _JUNK_PATH_MARKERS):
        return False
    if src.endswith(_JUNK_EXTS):
        return False
    snip = h.get("snip") or ""
    if not snip:
        return False
    # Binary / minified garbage: low ratio of letters+spaces to total chars.
    letters = sum(c.isalpha() or c.isspace() for c in snip)
    if letters / max(len(snip), 1) < 0.6:
        return False
    return True


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        _emit({})
        return

    if payload.get("hook_event_name") not in (None, "pre_llm_call"):
        _emit({})
        return

    extra = payload.get("extra") or {}
    session_id = payload.get("session_id")
    user_message = extra.get("user_message") or ""
    platform = extra.get("platform") or ""

    parts = []

    who = _interlocutor(session_id, platform)
    if who:
        parts.append(f"[Aura context] You are talking to: {who}. Keep the two people straight.")
    else:
        parts.append("[Aura context] You are Aura, on the Beelink.")

    hits = _recall(user_message)
    if hits:
        lines = ["[Recalled from your memory — via search_rag, may or may not be relevant:]"]
        for h in hits:
            sim = h.get("sim")
            tag = f" ({sim})" if sim is not None else ""
            name = h.get("name") or (h.get("src") or "?").split("/")[-1]
            snip = h.get("snip") or ""
            lines.append(f"- «{name}»{tag}: {snip}")
        parts.append("\n".join(lines))

    text = "\n\n".join(parts).strip()
    _emit({"context": text} if text else {})


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Absolute last resort — never break the turn.
        try:
            _emit({})
        except Exception:
            pass
