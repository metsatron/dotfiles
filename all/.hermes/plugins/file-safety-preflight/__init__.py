# __init__.py


# [[file:../../../DotCortex/hermes.org::*__init__.py][__init__.py:1]]
"""File safety preflight hook for Hermes.

Intercepts write operations and enforces the Git Safety Covenant.
"""

import subprocess
import os
import json
import datetime
import re
from pathlib import Path

# Tools that write to files
WRITE_TOOLS = {"patch", "writefile", "write_file", "create_file"}

# Terminal commands that write to files
WRITE_PATTERNS = re.compile(
    r'(\bsed\s+-i|\btee\b|\becho\b.*>|\bcp\b|\bmv\b|\bdd\b|\btruncate\b|>\s*\S)',
    re.IGNORECASE
)

# Covenant message injected on every turn
GIT_COVENANT = """[SOVEREIGNTY COVENANT — fires every turn]

Before calling patch, writefile, write_file, create_file, or any terminal command
that writes to disk: run `git diff HEAD -- <file>` on the specific file.

If the file has uncommitted changes you did not make, STOP and report.
Do not proceed. This is not a suggestion. Violations are logged.
"""

def preflight(tool_name: str, args: dict, task_id: str, ctx, **kwargs):
    """Pre-tool-call hook: intercept write operations and check git status."""
    if tool_name not in WRITE_TOOLS and tool_name != "terminal":
        return
    
    # Extract file path from tool args
    file_path = None
    if tool_name in WRITE_TOOLS:
        file_path = args.get("path") or args.get("file_path") or args.get("target")
    elif tool_name == "terminal":
        cmd = args.get("command") or args.get("cmd", "")
        # Check if terminal command writes to files
        if not WRITE_PATTERNS.search(cmd):
            return
        # For terminal commands, we can't reliably extract all file paths from
        # arbitrary bash commands, so we just warn
        ctx.inject_message(
            f"[PREFLIGHT WARNING] terminal command appears to write to disk:\n"
            f"  {cmd[:300]}\n"
            f"Confirm this is intentional and files are in a clean git state.",
            role="user"
        )
        return
    
    if not file_path:
        return
    
    # Convert to absolute path
    try:
        abs_path = Path(file_path).expanduser().resolve()
        repo_dir = abs_path.parent
        
        # Check git status for this specific file
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", str(abs_path)],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.stdout.strip():
            # File has uncommitted changes from prior session
            ctx.inject_message(
                f"[COVENANT VIOLATION INTERCEPTED]\n"
                f"Tool `{tool_name}` was called on `{abs_path}` which has uncommitted changes "
                f"from a prior session that you did not make.\n"
                f"STOP. Do not touch this file. Report the conflict to Mètsàtron.",
                role="user"
            )
    except subprocess.TimeoutExpired:
        # SSHFS timeout - warn but don't block
        ctx.inject_message(
            f"[PREFLIGHT WARNING] git diff timed out for `{abs_path}`. "
            f"Proceed only with explicit confirmation.",
            role="user"
        )
    except Exception:
        # Git not available, not a repo, etc. - silently allow
        pass


def postflight(tool_name: str, args: dict, result: str, task_id: str, **kwargs):
    """Post-tool-call hook: log all write operations."""
    if tool_name not in WRITE_TOOLS:
        return
    
    file_path = args.get("path") or args.get("file_path") or args.get("target")
    
    # Log to audit trail
    log = Path.home() / ".hermes" / "logs" / "file-writes.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "ts": datetime.datetime.now().isoformat(),
        "tool": tool_name,
        "file": file_path,
        "task_id": task_id,
        "result": result[:500]  # Truncate long results
    }
    
    with open(log, "a") as f:
        f.write(json.dumps(entry) + "\n")


def register(ctx):
    """Register hooks with Hermes plugin system."""
    # Covenant injection - runs before every LLM call
    def inject_covenant(**kwargs):
        return {"context": GIT_COVENANT}
    
    ctx.register_hook("pre_llm_call", inject_covenant)
    ctx.register_hook("pre_tool_call", preflight)
    ctx.register_hook("post_tool_call", postflight)
# __init__.py:1 ends here
