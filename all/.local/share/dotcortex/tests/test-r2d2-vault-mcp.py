#!/usr/bin/env python3
"""vault_block must stop a vault path in the arguments of any mcp_* tool."""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parents[4] / ".hermes" / "r2d2" / "hook_tool.py"
STUB = '''
from pathlib import Path
HOME = Path("/home/gille")
SECRET_VAULT = HOME / "Secret Vault"
STATE_DIR = Path("/tmp/r2d2-vault-mcp-test-state")
def mode(feature): return "active"
def log(*a, **k): pass
def who(sid): return "metsatron"
'''
PATHFIX = "PATH_ARGS = {}\n"

CASES = [
    ("hermes-named mcp read of a vault path", "mcp__genoffice__sheet_read",
     {"file": "/home/gille/Secret Vault/Reports/x/a.xlsx"}, True),
    ("hermes-named mcp read outside the vault", "mcp__genoffice__sheet_read", {"file": "/tmp/ok.xlsx"}, False),
    ("mcp read of a vault path", "mcp_genoffice_xlsx_read",
     {"path": "/home/gille/Secret Vault/Reports/x/a.xlsx"}, True),
    ("mcp convert of a tilde vault path", "mcp_genoffice_convert",
     {"input": "~/Secret Vault/n.docx", "output": "/tmp/n.pdf"}, True),
    ("mcp call with a vault glob", "mcp_anything_search", {"q": "secret*"}, True),
    ("mcp call outside the vault", "mcp_genoffice_xlsx_read", {"path": "/tmp/ok.xlsx"}, False),
    ("mcp call stating the boundary", "mcp_genoffice_docx_write",
     {"path": "/tmp/n.md", "text": "No clinical data here; the Secret Vault stays closed."}, False),
    ("builtin read_file still blocked", "read_file", {"path": "/home/gille/Secret Vault/a.md"}, True),
    ("unrelated tool not inspected", "web_search", {"q": "/home/gille/Secret Vault/"}, False),
]


def main() -> int:
    assert HOOK.is_file(), HOOK
    with tempfile.TemporaryDirectory() as td:
        live = Path(td)
        (live / "r2d2lib.py").write_text(STUB)
        (live / "pathfix.py").write_text(PATHFIX)
        link = live / "hook_tool.py"
        os.symlink(HOOK, link)
        spec = importlib.util.spec_from_file_location("hook_tool_under_test", link)
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(live))
        spec.loader.exec_module(mod)
        bad = 0
        for name, tool, args, expect_block in CASES:
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    mod.vault_block(tool, args)
                blocked = False
            except SystemExit:
                blocked = '"block"' in buf.getvalue()
            ok = blocked == expect_block
            bad += not ok
            print(("ok   " if ok else "FAIL ") + name + (" (blocked)" if blocked else " (allowed)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
