#!/usr/bin/env python3
"""Fail-closed deterministic PermissionRequest rule engine for SO-APPROVAL P3."""

import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import signal
import stat
import sys


SCHEMA_VERSION = "so-approval-p3.v1"
HARD_TIMEOUT_SECONDS = 0.75
CLASS_NAMES = (
    "ssh-kikin-readonly",
    "local-test-run",
    "centre-render",
    "dotcortex-safe-commit",
    "outbound-tool-call",
)
ALLOW_OUTPUT = {
    "hookSpecificOutput": {
        "hookEventName": "PermissionRequest",
        "decision": {"behavior": "allow"},
    }
}
SHELL_META_RE = re.compile(r"(?:[\n\r;]|&&|\|\||\$\(|`|[<>])")
SSH_RE = re.compile(
    r"^ssh -o BatchMode=yes ([A-Za-z0-9._-]+) '([^'\n\r]+)'$"
)
UNITTEST_RE = re.compile(
    r"^(?:python3|/usr/bin/python3) -m unittest "
    r"(FORGE\.tests\.[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)$"
)
PYTEST_RE = re.compile(
    r'^pytest ([A-Za-z0-9_./-]+) -q -m "not live"$'
)
CENTRE_COMMANDS = {
    "/usr/bin/python3 FORGE/bin/pokemon-centre render",
    "FORGE/bin/clubhouse-bosses-refresh",
}
READERS = {
    "cat",
    "head",
    "tail",
    "grep",
    "ls",
    "stat",
    "wc",
    "mailcortex",
    "pgrep",
    "date",
    "find",
}
GIT_READERS = {"log", "status", "diff", "show"}
FIND_WRITE_ACTIONS = {
    "-delete",
    "-exec",
    "-execdir",
    "-ok",
    "-okdir",
    "-fprint",
    "-fprint0",
    "-fprintf",
    "-fls",
}
GIT_UNSAFE_READ_OPTIONS = {
    "--ext-diff",
    "--textconv",
    "--exec-path",
    "--paginate",
}


class Rejected(ValueError):
    """Input is outside the exact allow shape."""


def _manifest_path():
    override = os.environ.get("SO_APPROVAL_P3_MANIFEST")
    if override:
        return Path(override)
    installed = Path.home() / ".config/dotcortex/claude-approval-p3.json"
    if installed.is_file():
        return installed
    source_tree = Path(__file__).resolve().parents[3]
    return source_tree / ".config/dotcortex/claude-approval-p3.json"


def _load_manifest():
    path = _manifest_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {
        "schema_version",
        "readonly_host",
        "repo_roots",
        "tmp_roots",
        "outbound_tools",
        "classes",
    }:
        raise Rejected("manifest keys")
    if data["schema_version"] != SCHEMA_VERSION:
        raise Rejected("manifest version")
    if not isinstance(data["readonly_host"], str) or not re.fullmatch(
        r"[A-Za-z0-9._-]+", data["readonly_host"]
    ):
        raise Rejected("readonly host")
    if not isinstance(data["repo_roots"], list) or not data["repo_roots"]:
        raise Rejected("repo roots")
    roots = []
    for raw in data["repo_roots"]:
        if not isinstance(raw, str) or not raw.startswith("/"):
            raise Rejected("repo root")
        root = Path(raw).resolve(strict=False)
        if root == Path("/"):
            raise Rejected("broad repo root")
        roots.append(root)
    if not isinstance(data["tmp_roots"], list) or not data["tmp_roots"]:
        raise Rejected("tmp roots")
    tmp_roots = []
    for raw in data["tmp_roots"]:
        if not isinstance(raw, str) or not raw.startswith("/"):
            raise Rejected("tmp root")
        root = Path(raw).resolve(strict=False)
        if root == Path("/"):
            raise Rejected("broad tmp root")
        tmp_roots.append(root)
    if not isinstance(data["outbound_tools"], list) or not all(
        isinstance(item, str) and item for item in data["outbound_tools"]
    ):
        raise Rejected("outbound tools")
    classes = data["classes"]
    if not isinstance(classes, list) or len(classes) != len(CLASS_NAMES):
        raise Rejected("classes")
    enabled = {}
    for expected, item in zip(CLASS_NAMES, classes):
        if (
            not isinstance(item, dict)
            or set(item) != {"name", "enabled"}
            or item.get("name") != expected
            or type(item.get("enabled")) is not bool
        ):
            raise Rejected("class entry")
        enabled[expected] = item["enabled"]
    data["repo_roots"] = roots
    data["tmp_roots"] = tmp_roots
    data["enabled"] = enabled
    return data


def _protected_token(token):
    lowered = token.lower().replace("\\", "/")
    components = [part for part in lowered.split("/") if part]
    if "/home/gille" in lowered or "secret vault" in lowered:
        return True
    if ".git" in components or ".ssh" in components or ".env" in components:
        return True
    if "nexus/keys" in lowered:
        return True
    names = {
        ".netrc",
        ".authinfo",
        ".authinfo.gpg",
        "authorized_keys",
        "credentials",
        "credentials.json",
        "auth.json",
        "secrets.json",
        "id_rsa",
        "id_ed25519",
    }
    return any(part in names for part in components)


def _hard_never(command):
    if not isinstance(command, str) or not command or "\x00" in command:
        return True
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return True
    lowered = [word.lower() for word in words]
    joined = " ".join(lowered)
    if any(_protected_token(word) for word in words):
        return True
    if re.search(r"(?:^|[;&|]\s*)git\s+(?:push|reset|revert)(?:\s|$)", joined):
        return True
    if re.search(r"(?:^|[;&|]\s*)git\s+worktree\s+prune(?:\s|$)", joined):
        return True
    if lowered and lowered[0] == "rm" and any(
        word == "--recursive" or (word.startswith("-") and "r" in word[1:])
        for word in lowered[1:]
    ):
        return True
    if any(word in {"sudo", "rc-service", "systemctl", "tailscale", "crontab"} for word in lowered):
        return True
    install_pairs = {
        "apt install",
        "apt-get install",
        "apk add",
        "dnf install",
        "yum install",
        "pacman -s",
        "zypper install",
        "brew install",
        "pip install",
        "pip3 install",
        "pipx install",
        "npm install",
        "npm i",
        "pnpm install",
        "yarn add",
        "cargo install",
        "guix install",
        "guix package",
    }
    if any(pair in joined for pair in install_pairs):
        return True
    if re.search(r"(?:python3|/usr/bin/python3)\s+-m\s+pip\s+install(?:\s|$)", joined):
        return True
    return False


def _inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _cwd_and_root(event, roots, exact=False):
    raw = event.get("cwd")
    if not isinstance(raw, str) or not raw.startswith("/"):
        raise Rejected("cwd")
    cwd = Path(raw).resolve(strict=False)
    for root in roots:
        if cwd == root or (not exact and _inside(cwd, root)):
            return cwd, root
    raise Rejected("cwd outside roots")


def _safe_relative_path(raw):
    if not raw or raw.startswith("/") or raw.startswith("~") or raw.startswith(":"):
        return False
    path = PurePosixPath(raw)
    if any(part in {"", ".", ".."} for part in path.parts):
        return False
    return not _protected_token(raw)


def _remote_argument_paths_safe(words):
    for word in words[1:]:
        candidates = [word]
        if "=" in word:
            candidates.append(word.split("=", 1)[1])
        for candidate in candidates:
            if _protected_token(candidate):
                return False
    return True


def _reader_segment(segment):
    try:
        words = shlex.split(segment, posix=True)
    except ValueError:
        return False
    if not words or not _remote_argument_paths_safe(words):
        return False
    command = words[0]
    if command == "git":
        if len(words) < 2 or words[1] not in GIT_READERS:
            return False
        for word in words[2:]:
            if word in GIT_UNSAFE_READ_OPTIONS or word.startswith("--output="):
                return False
        return True
    if command not in READERS:
        return False
    if command == "mailcortex":
        return len(words) >= 2 and words[1] in {"inbox", "read"}
    if command == "find":
        return not any(
            word in FIND_WRITE_ACTIONS or any(word.startswith(item + "=") for item in FIND_WRITE_ACTIONS)
            for word in words[1:]
        )
    if command == "tail" and any(word in {"-f", "--follow"} or word.startswith("--follow=") for word in words[1:]):
        return False
    return True


def _ssh_readonly(command, manifest):
    match = SSH_RE.fullmatch(command)
    if not match or match.group(1) != manifest["readonly_host"]:
        return False
    remote = match.group(2)
    if SHELL_META_RE.search(remote.replace("|", "")):
        return False
    if "||" in remote or remote.startswith("|") or remote.endswith("|"):
        return False
    if _hard_never(remote):
        return False
    parts = [part.strip() for part in remote.split("|")]
    return bool(parts) and all(part and _reader_segment(part) for part in parts)


def _local_test(command, event, manifest):
    cwd, root = _cwd_and_root(event, manifest["repo_roots"])
    if SHELL_META_RE.search(command):
        return False
    if UNITTEST_RE.fullmatch(command):
        return True
    match = PYTEST_RE.fullmatch(command)
    if not match or not _safe_relative_path(match.group(1)):
        return False
    target = (cwd / match.group(1)).resolve(strict=False)
    try:
        info = target.lstat()
    except OSError:
        return False
    return _inside(target, root) and stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)


def _centre(command, event, manifest):
    cwd, _root = _cwd_and_root(event, manifest["repo_roots"], exact=True)
    if command not in CENTRE_COMMANDS:
        return False
    script = "FORGE/bin/pokemon-centre" if command.startswith("/usr/bin/python3 ") else command
    target = (cwd / script).resolve(strict=False)
    try:
        info = target.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)


def _safe_commit(command, event, manifest):
    cwd, root = _cwd_and_root(event, manifest["repo_roots"], exact=True)
    if cwd != root or SHELL_META_RE.search(command) or _hard_never(command):
        return False
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return False
    if len(words) < 6 or words[:2] != ["git", "commit"] or words[2] != "-F":
        return False
    try:
        separator = words.index("--", 4)
    except ValueError:
        return False
    if separator != 4 or not words[5:]:
        return False
    message = Path(words[3])
    if not message.is_absolute():
        message = cwd / message
    try:
        info = message.lstat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        return False
    if info.st_uid != os.getuid() or not any(
        _inside(message.resolve(strict=False), root) and message.resolve(strict=False) != root
        for root in manifest["tmp_roots"]
    ):
        return False
    for raw in words[5:]:
        if not _safe_relative_path(raw):
            return False
        target = (cwd / raw).resolve(strict=False)
        try:
            target_info = target.lstat()
        except OSError:
            return False
        if (
            not _inside(target, root)
            or not stat.S_ISREG(target_info.st_mode)
            or stat.S_ISLNK(target_info.st_mode)
        ):
            return False
    return True


def _protected_tool_input(tool_input):
    try:
        raw = json.dumps(tool_input, ensure_ascii=False, sort_keys=True).lower().replace("\\\\", "/")
    except (TypeError, ValueError):
        return True
    return any(
        marker in raw
        for marker in (
            "/home/gille",
            "secret vault",
            "nexus/keys",
            "/.ssh/",
            "~/.ssh/",
            "/.env",
            "auth.json",
            "credentials.json",
            "oauth.json",
        )
    )


def _candidate(event, manifest):
    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        raise Rejected("tool event")
    if tool_name != "Bash":
        if tool_name in manifest["outbound_tools"] and not _protected_tool_input(tool_input):
            return "outbound-tool-call", True
        raise Rejected("unknown tool")
    if set(tool_input) != {"command"} or not isinstance(tool_input.get("command"), str):
        raise Rejected("bash input")
    command = tool_input["command"]
    if _hard_never(command):
        raise Rejected("hard never")
    parsers = (
        ("ssh-kikin-readonly", lambda: _ssh_readonly(command, manifest)),
        ("local-test-run", lambda: _local_test(command, event, manifest)),
        ("centre-render", lambda: _centre(command, event, manifest)),
        ("dotcortex-safe-commit", lambda: _safe_commit(command, event, manifest)),
    )
    matches = []
    for name, parser in parsers:
        try:
            if parser():
                matches.append(name)
        except (OSError, Rejected, ValueError):
            continue
    if len(matches) != 1:
        raise Rejected("no unique rule")
    return matches[0], True


def evaluate(event, manifest):
    if not isinstance(event, dict) or event.get("hook_event_name") != "PermissionRequest":
        raise Rejected("event")
    rule, matched = _candidate(event, manifest)
    return bool(matched and manifest["enabled"].get(rule) is True)


def _deadline(_signum, _frame):
    raise TimeoutError("approval deadline")


def main():
    try:
        previous_handler = signal.signal(signal.SIGALRM, _deadline)
        signal.setitimer(signal.ITIMER_REAL, HARD_TIMEOUT_SECONDS)
    except Exception:
        return 0
    try:
        raw = sys.stdin.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise Rejected("input too large")
        event = json.loads(raw)
        manifest = _load_manifest()
        if evaluate(event, manifest):
            sys.stdout.write(json.dumps(ALLOW_OUTPUT, separators=(",", ":")))
            sys.stdout.write("\n")
    except Exception:
        pass
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
