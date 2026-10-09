#!/usr/bin/env python3
"""Fail-closed local approval engine for Kikin's Claude consorts."""

import json
import os
from pathlib import Path
import posixpath
import re
import shlex
import signal
import stat
import sys


SCHEMA = "hc.approval.canary.kikin.manifest.v1"
VERSION = "claude-approval-canary.kikin.v1"
CLASS_NAMES = ("local_read", "git_observe", "centre_render", "safe_commit")
ALLOW_OUTPUT = {
    "hookSpecificOutput": {
        "hookEventName": "PermissionRequest",
        "decision": {"behavior": "allow"},
    }
}
SHELL_META = re.compile(r"(?:[\n\r;]|&&|\|\||\$\(|`|[<>]|&|\\)")
PATH_META = re.compile(r"(?:[*?\[\]{}]|\$|`)")
REMOTE = {"ssh", "scp", "rsync", "curl", "wget", "nc", "socat", "telnet"}
SERVICE = {"sudo", "systemctl", "rc-service", "crontab", "tailscale"}
PACKAGE = {"apt", "apt-get", "apk", "brew", "cargo", "conda", "dnf", "guix", "gem", "mamba", "npm", "pacman", "pip", "pip3", "pipx", "pnpm", "poetry", "uv", "yarn", "yum", "zypper"}
AUTH = {".authinfo", ".authinfo.gpg", ".netrc", "auth.json", "authorized_keys", "credentials", "credentials.json", "id_ed25519", "id_rsa", "oauth.json", "oauth_creds.json", "secrets.json", "cookies.sqlite", "cookies.jar"}
READ_OPTIONS = {"-n", "-i", "-v", "-E", "-F", "-h", "-H", "--line-number", "--ignore-case"}
FIND_OPTIONS = {"-maxdepth", "-mindepth", "-type", "-name", "-iname", "-path", "-ipath", "-print", "-print0", "-mount", "-xdev"}
# Compound commands (2026-10-09): agents write `cd X && sed -n 1,60p f | cut -c1-200`.
# A compound is considered only when it contains nothing but the separators below;
# any redirection, substitution, backslash, background `&` or newline stays at the hard floor.
DISCARDS = (" 2>/dev/null", " 2> /dev/null", " >/dev/null", " > /dev/null", " 2>&1")
SEPARATORS = ("&&", "||", "|", ";")
TOOL_INPUT_KEYS = {"command", "description", "timeout"}
# Bundled short flags that only change how matches or listings are printed.
# grep -r/-R stays out: recursion would walk past the per-path protected check.
GREP_FLAGS = re.compile(r"^-[nivEFhHlLwxcoIs]+$")
LS_FLAGS = re.compile(r"^-[alhtrdAF1S]+$")
SED_PRINT = re.compile(r"^(?:\d+|\$)(?:,(?:\d+|\$))?p$")
COUNT_VALUE = re.compile(r"^\+?\d+$")
FILTERS = {"head", "tail", "cut", "sort", "uniq", "wc", "tr", "grep", "sed"}
BRANCH_OPTIONS = {"-a", "--all", "-r", "--remotes", "-v", "-vv", "--verbose", "--show-current", "--no-color"}


def _inside(path, root):
    try:
        Path(path).relative_to(root)
        return True
    except ValueError:
        return False


def _protected(value):
    lowered = str(value).replace("\\", "/").casefold()
    parts = tuple(part for part in lowered.split("/") if part)
    if "palmcortex" in parts or any(parts[i:i + 3] == ("logs", "telegram", "personal") for i in range(max(0, len(parts) - 2))):
        return True
    if "secret vault" in lowered or "/home/gille" in lowered or "nexus/keys" in lowered:
        return True
    if any(part in {".ssh", ".secrets", "private", "secrets", "keys", "credentials"} for part in parts):
        return True
    basename = parts[-1] if parts else ""
    return basename in AUTH or basename.startswith(".env") or basename.endswith((".token", ".key", ".pem", ".kdbx", ".sqlite")) or "token" in basename or "secret" in basename or "cookie" in basename


def _hard_floor(event):
    try:
        raw = json.dumps(event.get("tool_input", {}), ensure_ascii=False, sort_keys=True).casefold()
    except (TypeError, ValueError):
        return True
    if _protected(raw) or "logs/telegram/personal" in raw or "palmcortex" in raw:
        return True
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return False
    if SHELL_META.search(command) and not _routes_compound(command):
        return True
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return True
    lowered = [word.casefold() for word in words]
    if any(word in REMOTE or word.startswith(("http://", "https://")) for word in lowered):
        return True
    if any(word in SERVICE or word in {"pkill", "killall"} for word in lowered):
        return True
    if lowered and lowered[0] == "kill" and (len(lowered) == 1 or any(word.startswith("-") for word in lowered[1:])):
        return True
    if "telegram-agent-host" in lowered and any(word in {"stop", "start", "switch", "bring"} for word in lowered):
        return True
    if "nurse-joy" in lowered and "revive" in lowered:
        return True
    if "tmux" in lowered and any(word.startswith("kill-") for word in lowered):
        return True
    if lowered and lowered[0] == "rm" and any(word == "-r" or word == "--recursive" or (word.startswith("-") and "r" in word[1:]) for word in lowered[1:]):
        return True
    for index, word in enumerate(lowered):
        if word in PACKAGE and any(next_word in {"install", "add", "i", "sync"} for next_word in lowered[index + 1:index + 4]):
            return True
    return any(word in {"--output", "--exec", "--execdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"} or word.startswith("--output=") for word in lowered)


def _lexical(raw, cwd):
    if not isinstance(raw, str) or not raw or "\x00" in raw or PATH_META.search(raw):
        return None
    if raw == "~":
        raw = str(Path.home())
    elif raw.startswith("~/"):
        raw = str(Path.home()) + raw[1:]
    elif raw.startswith("~"):
        return None
    elif not raw.startswith("/"):
        raw = posixpath.join(cwd, raw)
    return posixpath.normpath(raw) if raw.startswith("/") else None


def _path(raw, cwd, roots, exists=True):
    lexical = _lexical(raw, cwd)
    if lexical is None or _protected(lexical):
        return None
    resolved = os.path.realpath(lexical)
    if not any(_inside(resolved, root) for root in roots):
        return None
    if exists and not os.path.exists(resolved):
        return None
    return resolved


def _scratch(raw, cwd, roots):
    lexical = _lexical(raw, cwd)
    if lexical is None:
        return None
    resolved = os.path.realpath(lexical)
    return resolved if any(_inside(resolved, root) and resolved != root for root in roots) else None


def _load_manifest():
    override = os.environ.get("SO_APPROVAL_KIKIN_MANIFEST")
    path = Path(override) if override else Path(__file__).resolve().parents[3] / ".config/dotcortex/claude-approval-canary.kikin.v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"schema", "manifest_version", "hard_floor_ids", "roots", "scratch_roots", "classes"} or data.get("schema") != SCHEMA or data.get("manifest_version") != VERSION:
        raise ValueError("invalid Kikin manifest")
    if not isinstance(data["hard_floor_ids"], list) or not isinstance(data["classes"], list) or len(data["classes"]) != len(CLASS_NAMES):
        raise ValueError("invalid Kikin manifest classes")
    roots = tuple(os.path.realpath(item) for item in data["roots"] if isinstance(item, str) and item.startswith("/"))
    scratch = tuple(os.path.realpath(item) for item in data["scratch_roots"] if isinstance(item, str) and item.startswith("/"))
    if len(roots) != len(data["roots"]) or len(scratch) != len(data["scratch_roots"]) or any(root == "/" for root in roots + scratch):
        raise ValueError("invalid Kikin roots")
    entries = {}
    for name, entry in zip(CLASS_NAMES, data["classes"]):
        if not isinstance(entry, dict) or entry.get("name") != name or type(entry.get("enabled")) is not bool:
            raise ValueError("invalid Kikin class")
        entries[name] = entry
    data["roots"] = roots
    data["scratch_roots"] = scratch
    data["entries"] = entries
    return data


def _targets(values, cwd, manifest, directories=None):
    paths = tuple(_path(value, cwd, manifest["roots"]) for value in values)
    if not paths or any(path is None for path in paths):
        return None
    if directories is True and any(not os.path.isdir(path) for path in paths):
        return None
    if directories is False and any(not os.path.isfile(path) for path in paths):
        return None
    return paths


def _repo(raw, cwd, manifest):
    path = _path(raw, cwd, manifest["roots"])
    if path is None:
        return None
    current = Path(path if os.path.isdir(path) else os.path.dirname(path))
    while True:
        if (current / ".git").exists() and any(_inside(str(current), root) for root in manifest["roots"]):
            return str(current)
        if current.parent == current:
            return None
        current = current.parent


def _local_match(event, manifest, words=None):
    entry = manifest["entries"].get("local_read")
    if entry is None:
        return False
    name, tool_input, cwd = event.get("tool_name"), event.get("tool_input"), event.get("cwd")
    if not isinstance(tool_input, dict) or not isinstance(cwd, str):
        return False
    cwd = _path(cwd, cwd, manifest["roots"])
    if cwd is None:
        return False
    if name == "Read":
        return bool(_targets([tool_input.get("file_path", tool_input.get("path"))], cwd, manifest, False))
    if name in {"Glob", "Grep"}:
        base = tool_input.get("path") or cwd
        pattern = tool_input.get("pattern")
        return bool(_targets([base], cwd, manifest, True) and isinstance(pattern, str) and pattern and ".." not in pattern.split("/"))
    if name != "Bash" or not set(tool_input) <= TOOL_INPUT_KEYS or not isinstance(tool_input.get("command"), str):
        return False
    if words is None:
        # A whole command: refuse shell syntax. _compound passes words it already
        # parsed with quotes respected, so a quoted backslash pattern is no threat there.
        if SHELL_META.search(tool_input["command"]):
            return False
        try:
            words = shlex.split(tool_input["command"], posix=True)
        except ValueError:
            return False
    if not words or words[0] not in entry["bash_verbs"] or words[0] != words[0].rsplit("/", 1)[-1]:
        return False
    verb, args = words[0], words[1:]
    if verb in {"head", "tail"}:
        args = _strip_counts(args)
        if args is None:
            return False
    if verb == "sed":
        if len(args) < 3 or args[0] != "-n" or not SED_PRINT.match(args[1]) or any(arg.startswith("-") for arg in args[2:]):
            return False
        return bool(_targets(args[2:], cwd, manifest, False))
    if verb == "grep":
        # Read-only flags may sit before or after the pattern (agents write grep -n PAT f);
        # the first non-flag word is the pattern, every later one is a file to check.
        if any(arg.startswith("-") and arg not in READ_OPTIONS and not GREP_FLAGS.match(arg) for arg in args):
            return False
        words_only = [arg for arg in args if not arg.startswith("-")]
        if len(words_only) < 2:
            return False
        operands = words_only[1:]
    elif verb == "find":
        split = next((index for index, arg in enumerate(args) if arg.startswith("-")), len(args))
        operands, expression = args[:split], args[split:]
        if not operands or any(arg in {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"} for arg in expression):
            return False
        if any(arg.startswith("-") and arg not in FIND_OPTIONS for arg in expression):
            return False
    elif verb == "ls":
        if any(arg.startswith("-") and not LS_FLAGS.match(arg) for arg in args):
            return False
        operands = [arg for arg in args if not arg.startswith("-")] or ["."]
    else:
        operands = [arg for arg in args if not arg.startswith("-")]
        if not operands or any(arg.startswith("-") and arg not in READ_OPTIONS for arg in args):
            return False
    return bool(_targets(operands, cwd, manifest))


def _git_match(event, manifest):
    entry = manifest["entries"].get("git_observe")
    tool_input, cwd = event.get("tool_input"), event.get("cwd")
    if entry is None or event.get("tool_name") != "Bash" or not isinstance(tool_input, dict) or not set(tool_input) <= TOOL_INPUT_KEYS or not isinstance(tool_input.get("command"), str) or not isinstance(cwd, str):
        return False
    try:
        words = shlex.split(tool_input["command"], posix=True)
    except ValueError:
        return False
    if not words or words[0] != "git":
        return False
    args = words[1:]
    repo_raw = cwd
    if args[:1] == ["-C"]:
        if len(args) < 3:
            return False
        repo_raw, args = args[1], args[2:]
    if not args or args[0] not in entry["subcommands"]:
        return False
    repo = _repo(repo_raw, cwd, manifest)
    if repo is None:
        return False
    subcommand, remainder = args[0], args[1:]
    if any(item in {"--exec-path", "--ext-diff", "--textconv", "--paginate", "--output"} or item.startswith(("--exec-path=", "--git-dir=", "--work-tree=", "--output=")) for item in remainder):
        return False
    if subcommand == "branch":
        return all(item in BRANCH_OPTIONS for item in remainder)
    disk = []
    if "--" in remainder:
        if remainder.count("--") != 1:
            return False
        index = remainder.index("--")
        disk, remainder = remainder[index + 1:], remainder[:index]
        if not disk:
            return False
    if subcommand == "show":
        for item in remainder:
            if ":" in item:
                object_path = item.split(":", 1)[1]
                if not object_path or object_path.startswith("/") or _protected(object_path) or not _inside(posixpath.normpath(posixpath.join(repo, object_path)), repo):
                    return False
    if any(PATH_META.search(item) for item in disk) or any(item.startswith("-") for item in disk):
        return False
    return bool(_targets(disk or [repo], repo, manifest))


def _centre_match(event, manifest):
    entry = manifest["entries"].get("centre_render")
    tool_input, cwd = event.get("tool_input"), event.get("cwd")
    if entry is None or event.get("tool_name") != "Bash" or not isinstance(tool_input, dict) or set(tool_input) != {"command"} or not isinstance(cwd, str):
        return False
    try:
        words = shlex.split(tool_input["command"], posix=True)
    except ValueError:
        return False
    output = None
    if "--out" in words:
        index = words.index("--out")
        if words.count("--out") != 1 or index + 1 >= len(words):
            return False
        output = _scratch(words[index + 1], cwd, manifest["scratch_roots"])
        if output is None:
            return False
        del words[index:index + 2]
    command = " ".join(words)
    if command not in entry["commands"]:
        return False
    root = _repo(cwd, cwd, manifest)
    if root is None or Path(root).name.casefold() not in {"helmcortex", "dotcortex"}:
        return False
    script = "FORGE/bin/pokemon-centre" if "pokemon-centre" in command else "FORGE/bin/clubhouse-bosses-refresh"
    script_path = _path(script, root, manifest["roots"])
    return bool(script_path and os.path.isfile(script_path) and (output is None or output.startswith("/")))


def _safe_commit(event, manifest):
    entry = manifest["entries"].get("safe_commit")
    tool_input, cwd = event.get("tool_input"), event.get("cwd")
    if entry is None or event.get("tool_name") != "Bash" or not isinstance(tool_input, dict) or set(tool_input) != {"command"} or not isinstance(cwd, str):
        return False
    try:
        words = shlex.split(tool_input["command"], posix=True)
    except ValueError:
        return False
    if not words or words[0] not in {"git", "dotcortex-safe-commit"}:
        return False
    command, args = words[0], words[1:]
    repo_raw = cwd
    if args[:1] == ["-C"]:
        if len(args) < 2:
            return False
        repo_raw, args = args[1], args[2:]
    repo = _repo(repo_raw, cwd, manifest)
    if repo is None or (command == "dotcortex-safe-commit" and Path(repo).name.casefold() != "dotcortex"):
        return False
    if command == "git":
        if len(args) < 4 or args[:2] != ["commit", "-F"]:
            return False
        message, args = args[2], args[3:]
    else:
        if len(args) < 3 or args[0] != "-F":
            return False
        message, args = args[1], args[2:]
    if args[:1] != ["--"] or len(args) < 2:
        return False
    paths = args[1:]
    if any(not path or path.startswith("/") or path in {".", ".."} or PATH_META.search(path) or path.startswith(":") or ".." in Path(path).parts for path in paths):
        return False
    message = _scratch(message, repo, manifest["scratch_roots"])
    targets = _targets(paths, repo, manifest, False)
    if message is None or targets is None:
        return False
    try:
        info = os.lstat(message)
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode) and info.st_uid == os.getuid() and not stat.S_IMODE(info.st_mode) & 0o077 and all(not _protected(path) and ".git" not in Path(path).parts for path in targets)


def _strip_counts(args):
    """Drop head/tail line or byte counts (-n N, -c N, -N, --lines=N); None if malformed."""
    kept, index = [], 0
    while index < len(args):
        arg = args[index]
        if arg in {"-n", "-c"}:
            if index + 1 >= len(args) or not COUNT_VALUE.match(args[index + 1]):
                return None
            index += 2
            continue
        if re.fullmatch(r"-\d+", arg) or re.fullmatch(r"--(?:lines|bytes)=\+?\d+", arg) or arg == "-q":
            index += 1
            continue
        kept.append(arg)
        index += 1
    return kept


def _split_compound(command):
    """Split on top-level &&, ||, | and ; outside quotes, dropping harmless stderr/stdout
    discards (2>/dev/null, >/dev/null, 2>&1). Returns [(separator, text), ...] or None.
    Single-quoted text is literal; anything that could substitute, redirect to a file,
    background or escape (outside single quotes) makes it None."""
    segments, current, quote, index, separator = [], [], None, 0, None
    while index < len(command):
        char = command[index]
        if quote == "'":
            if char == "'":
                quote = None
            current.append(char)
            index += 1
            continue
        if quote == '"':
            if char in {"`", "\\"} or command.startswith("$(", index):
                return None
            if char == '"':
                quote = None
            current.append(char)
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            index += 1
            continue
        discard = next((d for d in DISCARDS if command.startswith(d, index)), None)
        if discard:
            index += len(discard)
            continue
        found = next((sep for sep in SEPARATORS if command.startswith(sep, index)), None)
        if found:
            segments.append((separator, "".join(current).strip()))
            current, separator = [], found
            index += len(found)
            continue
        if char in {"\n", "\r", "`", "<", ">", "\\", "&"} or command.startswith("$(", index):
            return None
        current.append(char)
        index += 1
    if quote:
        return None
    segments.append((separator, "".join(current).strip()))
    if any(not text for _, text in segments):
        return None
    return segments


def _routes_compound(command):
    """True when the command should be judged stage by stage by _compound."""
    segments = _split_compound(command)
    return segments is not None and (len(segments) > 1 or bool(SHELL_META.search(command)))


def _filter_ok(words):
    """A pipe stage that only transforms stdin: no file operands, no writing options."""
    verb, args = words[0], words[1:]
    if verb not in FILTERS or verb != verb.rsplit("/", 1)[-1]:
        return False
    if verb in {"head", "tail"}:
        return _strip_counts(args) == []
    if verb == "wc":
        return all(arg in {"-l", "-c", "-w", "-m"} for arg in args)
    if verb == "uniq":
        return all(arg in {"-c", "-d", "-u", "-i"} for arg in args)
    if verb == "tr":
        options = [arg for arg in args if arg.startswith("-")]
        return all(arg in {"-d", "-s"} for arg in options) and 1 <= len(args) - len(options) <= 2
    if verb == "sed":
        return len(args) == 2 and args[0] == "-n" and bool(SED_PRINT.match(args[1]))
    if verb == "grep":
        operands = [arg for arg in args if not arg.startswith("-")]
        return len(operands) == 1 and all(arg in READ_OPTIONS or GREP_FLAGS.match(arg) for arg in args if arg.startswith("-"))
    with_value = {"cut": {"-c", "-d", "-f", "-b"}, "sort": {"-k", "-t"}}[verb]
    flags = {"cut": {"-s"}, "sort": {"-n", "-r", "-u", "-h", "-V", "-f"}}[verb]
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in with_value and index + 1 < len(args):
            index += 2
        elif any(arg.startswith(option) and len(arg) > len(option) for option in with_value) or arg in flags:
            index += 1
        else:
            return False
    return True


def _compound(event, manifest):
    """Approve a compound only when every stage is a cd inside the roots, an enabled
    read or git observation, or (after a pipe) a stdin-only filter."""
    segments = _split_compound(event["tool_input"]["command"])
    cwd = _path(event.get("cwd"), event.get("cwd") or "/", manifest["roots"]) if isinstance(event.get("cwd"), str) else None
    if segments is None or cwd is None:
        return False, "no_match"
    used = []
    for separator, text in segments:
        try:
            words = shlex.split(text, posix=True)
        except ValueError:
            return False, "no_match"
        if words[:1] == ["timeout"] and len(words) > 2 and re.fullmatch(r"\d+(?:\.\d+)?[smh]?", words[1]):
            words = words[2:]
        if not words:
            return False, "no_match"
        if words[0] in {"true", "echo"}:
            # No redirection can survive _split_compound, so these only print or no-op.
            continue
        if separator == "|":
            if not _filter_ok(words):
                return False, "no_match"
            continue
        if words[0] == "cd":
            # Only a cd that must succeed for the chain to continue (start or after &&),
            # so later relative paths really resolve where this check resolved them.
            if separator not in (None, "&&"):
                return False, "no_match"
            target = _path(words[1], cwd, manifest["roots"]) if len(words) == 2 else None
            if target is None or not os.path.isdir(target):
                return False, "no_match"
            cwd = target
            continue
        stage = {**event, "cwd": cwd, "tool_input": {"command": shlex.join(words)}}
        for matcher, name in ((_local_match, "local_read"), (_git_match, "git_observe")):
            if (matcher(stage, manifest, words) if matcher is _local_match else matcher(stage, manifest)):
                if manifest["entries"][name]["enabled"] is not True:
                    return False, f"{name}_disabled"
                used.append(name)
                break
        else:
            return False, "no_match"
    if not used:
        return False, "no_match"
    return True, "compound:" + "+".join(sorted(set(used)))


def classify(event, manifest):
    """Return (allow, reason). The reason names the class that matched, or why none did."""
    if not isinstance(event, dict) or event.get("hook_event_name") != "PermissionRequest":
        return False, "not_permission_request"
    if _hard_floor(event):
        return False, "hard_floor"
    tool_input = event.get("tool_input")
    if event.get("tool_name") == "Bash" and isinstance(tool_input, dict) and set(tool_input) <= TOOL_INPUT_KEYS and isinstance(tool_input.get("command"), str) and _routes_compound(tool_input["command"]):
        return _compound(event, manifest)
    for matcher in (_local_match, _git_match, _centre_match, _safe_commit):
        if matcher(event, manifest):
            name = {"_local_match": "local_read", "_git_match": "git_observe", "_centre_match": "centre_render", "_safe_commit": "safe_commit"}[matcher.__name__]
            if manifest["entries"][name]["enabled"] is True:
                return True, name
            return False, f"{name}_disabled"
    return False, "no_match"


def evaluate(event, manifest):
    return classify(event, manifest)[0]


def _log_decision(event, allow, reason):
    # Decision ledger (2026-10-09): one JSON line per prompt, so prompts saved and
    # misfires can be measured. It never records tool_input itself (commands and
    # paths can carry secrets), only a short digest for correlation. Logging must
    # never change the decision, so every failure here is swallowed.
    try:
        import datetime
        import hashlib
        path = Path(os.environ.get("SO_APPROVAL_KIKIN_LOG") or Path.home() / ".local/state/dotcortex/claude-approval-kikin.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        event = event if isinstance(event, dict) else {}
        digest = hashlib.sha256(json.dumps(event.get("tool_input"), sort_keys=True, default=str).encode()).hexdigest()[:12]
        record = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "session": str(event.get("session_id") or "")[:64],
            "tool": str(event.get("tool_name") or "")[:64],
            "decision": "allow" if allow else "ask",
            "reason": reason,
            "input_sha": digest,
        }
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as fh:
            fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    except Exception:
        pass


def _deadline(_signal, _frame):
    raise TimeoutError("approval deadline")


def main():
    try:
        previous = signal.signal(signal.SIGALRM, _deadline)
        signal.setitimer(signal.ITIMER_REAL, 3.0)
    except Exception:
        return 0
    try:
        raw = sys.stdin.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("input too large")
        event = json.loads(raw)
        allow, reason = classify(event, _load_manifest())
        if allow:
            sys.stdout.write(json.dumps(ALLOW_OUTPUT, separators=(",", ":")) + "\n")
        _log_decision(event, allow, reason)
    except Exception as exc:
        _log_decision(None, False, f"error:{type(exc).__name__}")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
