# __init__.py - the gate

# #+NAME: plugin-protocol-gate-init

# [[file:../../../../agents-hermes.org::plugin-protocol-gate-init][plugin-protocol-gate-init]]
"""Protocol gate: no repository work and no coordinator mail without a claimed hole."""

import json
import os
import pathlib
import re

REPO = pathlib.Path("/home/metsatron/HelmCortex").resolve()  # NFS path resolves to mnt/x230; compare resolved
COURSES = REPO / "ROOTS" / "PromptGolf" / "courses"
SPEAKER = os.environ.get("HERMES_PROTOCOL_SPEAKER", "hermes-agent")

WRITE_TOOLS = {"patch", "write_file", "writefile", "create_file"}
GATED_COMMANDS = re.compile(
    r"git\s+commit|git\s+worktree\s+add|git\s+rm\b|mailcortex\s+send", re.IGNORECASE
)
FREE_ROOTS = ("/home/metsatron/.hermes/cache/", "/tmp/")


def _holes():
    for path in COURSES.glob("*/holes/active/*.json"):
        try:
            yield path, json.loads(path.read_text())
        except Exception:
            continue


def _swing_is_open(swing):
    """A swing is open until a lie closes it. `update-lie` is the closing verb."""
    lie = swing.get("lie")
    return not lie or str(lie).strip().lower() in ("", "none")


def _claim():
    """(claimed, reason, hole_id). Claimed means: a hole assigned to me with an open swing."""
    assigned = []
    for _path, hole in _holes():
        if hole.get("assigned_speaker") != SPEAKER:
            continue
        swings = hole.get("swings") or []
        open_now = [s for s in swings if isinstance(s, dict) and _swing_is_open(s)]
        assigned.append((hole.get("id"), open_now, len(swings)))
    if not assigned:
        return False, (
            "no active PromptGolf hole has assigned_speaker=%r; open or adopt one first "
            "(FORGE/bin/prompt-golf tee-off|open|adopt, then assign)" % SPEAKER
        ), None
    for hole_id, open_now, total in assigned:
        if open_now:
            return True, "open swing on %s" % hole_id, hole_id
    detail = ", ".join("%s (%d swings, none open)" % (h, n) for h, _o, n in assigned)
    return False, "assigned holes hold no open swing: " + detail + (
        "; start one with FORGE/bin/prompt-golf record-swing"
    ), None


def _dispatch_conflict(command, args):
    """Outbound work mail must not land in a lane the operator already has in flight.

    A hole that is assigned to another speaker and in progress is their work. Reassigning it from here is an
    override of the operator, and both workers this happened to were right to push back. Stand-downs are the one
    legitimate message into such a lane.
    """
    body = ""
    path_text = args.get("body_file") or ""
    if path_text:
        try:
            body = pathlib.Path(path_text).expanduser().read_text()
        except Exception:
            body = ""
    body = body or args.get("body") or ""
    if not body:
        return None
    if "STAND DOWN" in body.upper() or "STANDDOWN" in body.upper():
        return None
    for _path, hole in _holes():
        hole_id = str(hole.get("id") or "")
        owner = hole.get("assigned_speaker")
        if not hole_id or not owner or owner == SPEAKER:
            continue
        if hole.get("status") != "in-progress":
            continue
        if re.search(r"\b%s\b" % re.escape(hole_id), body):
            return "hole %s is assigned to %s and already in progress" % (hole_id, owner)
    return None


def _under_repo(path_text):
    try:
        path = pathlib.Path(path_text).expanduser().resolve()
    except Exception:
        return False
    if any(str(path).startswith(free) for free in FREE_ROOTS):
        return False
    return str(path).startswith(str(REPO))


def _refusal(what, reason):
    return {
        "error": "PROTOCOL GATE REFUSED %s: %s" % (what, reason),
        "protocol": "promptgolf",
        "speaker": SPEAKER,
        "next": "open a hole and a swing, then retry",
    }


def gate(tool_name, args, next_call, **ctx):
    """tool_execution middleware: refuse, or proceed."""
    args = args or {}
    kind = None
    if tool_name == "terminal":
        command = args.get("command") or ""
        if "mailcortex" in command.lower() and " send" in command.lower():
            conflict = _dispatch_conflict(command, args)
            if conflict:
                return _refusal("dispatch", conflict + "; the operator's assignment outranks a coordinator unit")
    if tool_name in WRITE_TOOLS:
        target = args.get("path") or args.get("file_path") or args.get("target")
        if target and _under_repo(target):
            kind = "write to %s" % target
    elif tool_name == "terminal":
        command = args.get("command") or ""
        if GATED_COMMANDS.search(command):
            workdir = args.get("workdir") or os.getcwd()
            if _under_repo(workdir) or str(REPO) in command or "mailcortex" in command.lower():
                kind = "command: %s" % command.strip().splitlines()[0][:120]

    if kind is None:
        return next_call(args)
    claimed, reason, _hole = _claim()
    if claimed:
        return next_call(args)
    return _refusal(kind, reason)


def inject_state(**kwargs):
    """pre_llm_call: put the claim state in front of every turn."""
    claimed, reason, _hole = _claim()
    state = "CLAIMED: " + reason if claimed else "UNCLAIMED: " + reason
    line = (
        "[PROTOCOL GATE] %s. Repository writes, commits, worktree creation and coordinator mail are refused "
        "without an open swing on a hole assigned to %r." % (state, SPEAKER)
    )
    return {"context": line}


def register(ctx):
    ctx.register_middleware("tool_execution", gate)
    ctx.register_hook("pre_llm_call", inject_state)
# plugin-protocol-gate-init ends here
