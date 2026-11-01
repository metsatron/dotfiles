#!/usr/bin/env python3
"""Hermes post_llm_call voice delivery for Mètsàtron's seat.

RESTORED 2026-11-01.  The original source file was replaced by a symlink that
pointed at itself (ELOOP), so every voice delivery silently died.  The compiled
module survived at __pycache__/hermes_voice.cpython-313.pyc; this file runs that
surviving bytecode while the readable source is still missing, so speech works
again today instead of waiting on a reconstruction.

Contract (unchanged): Hermes invokes this with the hook payload on stdin; it
prints a JSON object and detaches synthesis/delivery to a worker.
  - ~/.hermes/hermes-voice.off      hard no-op
  - ~/.hermes/hermes-voice.speaker  Lane B: the S24 phone speaker
  - otherwise                       Lane A: a Telegram voice bubble

Replace this shim with real source once the original is recovered (borg).
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

PYC = (
    Path(__file__).resolve().parent
    / "__pycache__"
    / "hermes_voice.cpython-313.pyc"
)


def main() -> int:
    if sys.version_info[:2] != (3, 13):
        print(
            f"hermes_voice: compiled module is cpython-313 but this is "
            f"{sys.version_info.major}.{sys.version_info.minor}",
            file=sys.stderr,
        )
        return 1
    if not PYC.is_file():
        print(f"hermes_voice: compiled module missing at {PYC}", file=sys.stderr)
        return 1
    runpy.run_path(str(PYC), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
