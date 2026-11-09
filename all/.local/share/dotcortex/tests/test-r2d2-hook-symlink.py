#!/usr/bin/env python3
"""The R2D2 tool guard must import r2d2lib from the directory it is launched from."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parents[4] / ".hermes" / "r2d2" / "hook_tool.py"
STUB = 'import os, sys\nprint("IMPORTED-FROM-LAUNCH-DIR")\nsys.stdout.flush()\nos._exit(0)\n'


def run(script: Path) -> str:
    p = subprocess.run([sys.executable, str(script)], input="{}", capture_output=True, text=True, timeout=20)
    return p.stdout + p.stderr


def main() -> int:
    assert HOOK.is_file(), HOOK
    with tempfile.TemporaryDirectory() as td:
        live = Path(td) / "live"
        live.mkdir()
        (live / "r2d2lib.py").write_text(STUB)
        link = live / "hook_tool.py"
        os.symlink(HOOK, link)
        out = run(link)
        if "IMPORTED-FROM-LAUNCH-DIR" not in out:
            print("FAIL: guard did not find r2d2lib next to the symlink:\n" + out)
            return 1
    print("ok: guard imports its siblings through a symlink")
    return 0


if __name__ == "__main__":
    sys.exit(main())
