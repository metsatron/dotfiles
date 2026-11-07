#!/usr/bin/env python3
"""Aura recall-ingest hook (STAGED — not wired into config.yaml).

For on_session_end / on_compact: keep Odysseus recall current in near-real-time
instead of waiting for the daily 04:10 cron. Reads JSON on stdin, returns fast,
and fires the export+embed DETACHED under a non-blocking flock (overlapping
fires skip cleanly) so it never blocks or races Aura's turn.
"""
import json
import subprocess
import sys

LOCK = "/tmp/aura_recall_ingest.lock"
SH = "/home/gille/.hermes/agent-hooks/aura_recall_ingest.sh"


def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    try:
        subprocess.Popen(
            ["setsid", "flock", "-n", LOCK, "bash", SH],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        print(json.dumps({"ok": True, "ingest": "launched"}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)[:200]}))


if __name__ == "__main__":
    main()
