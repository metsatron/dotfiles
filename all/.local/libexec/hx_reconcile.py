"""Versioned bounded source reconciliation for the HX router."""
import base64
import hashlib
import io
import json
import os
import re
import shlex
import signal
import socket
import stat
import subprocess
import sys

PROTOCOL = "dotcortex-root-org-v1"
ADMISSION = "dotcortex-operational-root-org-v1"
MAGIC = b"HXRC\x00\x01\n"
MAX_FILES = 4096
MAX_FILE = 8 * 1024 * 1024
MAX_CONTENT = 64 * 1024 * 1024
MAX_MANIFEST = 1024 * 1024
MAX_ENVELOPE = 64 * 1024
MAX_FRAME = len(MAGIC) + 8 + MAX_MANIFEST + MAX_CONTENT + 32
SECONDS = 600
EXCLUDED = frozenset({
    "README.org", "CODE_OF_SOVEREIGNTY.org", "agents.org", "agents-hooks.org",
    "agents-mcp.org", "loom.org", "dotcortex.org", "claude.org",
})
LOCAL_FS = frozenset({"ext2", "ext3", "ext4", "btrfs", "xfs", "zfs", "f2fs",
                      "tmpfs", "ramfs", "overlay", "ubifs"})
TOOL_DIRS = frozenset({"FORGE/bin", "FORGE/VoxForge/bin", "FORGE/PixelForge/bin"})


class Refusal(Exception):
    def __init__(self, message, code=65):
        super().__init__(message)
        self.code = code


def require(condition, message, code=65):
    if not condition:
        raise Refusal(message, code)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def admitted(name):
    return (isinstance(name, str) and name not in {"", ".", ".."}
            and "/" not in name and "\\" not in name and "\x00" not in name
            and len(name.encode("utf-8")) <= 255 and name.endswith(".org")
            and name not in EXCLUDED and not name.startswith("agents-skills"))


def check_policy(entry):
    require(entry == {"class": "client-fanout-reconcile",
                      "reconcile": {"protocol": PROTOCOL}},
            "unsupported reconcile declaration", 78)


def classify(argv):
    require(isinstance(argv, list) and all(isinstance(a, str) and "\x00" not in a for a in argv),
            "invalid argv", 2)
    flags, root, finalize = set(), None, False
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "hub-finalize":
            require(not finalize, "duplicate hub-finalize", 2)
            finalize = True
        elif arg == "--source-root" or arg.startswith("--source-root="):
            require(root is None, "duplicate source-root", 2)
            if arg == "--source-root":
                index += 1
                require(index < len(argv), "source-root requires a path", 2)
                root = argv[index]
                require(not root.startswith("--"), "source-root requires a path", 2)
            else:
                root = arg.split("=", 1)[1]
            require(bool(root), "source-root requires a path", 2)
        elif arg in {"--source-only", "--logs-only", "--dry-run", "--skip-validate", "--help", "-h"}:
            flags.add(arg)
        else:
            raise Refusal(f"unsupported export argument: {arg!r}", 2)
        index += 1
    require(not {"--source-only", "--logs-only"} <= flags, "source-only conflicts with logs-only", 2)
    require(not (root is not None and ("--logs-only" in flags or finalize)),
            "source-root conflicts with logs-only/hub-finalize", 2)
    require(not (finalize and flags & {"--source-only", "--logs-only"}),
            "hub-finalize conflicts with source/log selection", 2)
    route = "hub" if finalize or flags & {"--logs-only", "--help", "-h"} else "client-fanout-reconcile"
    return route, root


def local_root(root, cwd):
    selected = os.path.expanduser(root) if root is not None else os.path.expanduser("~/DotCortex")
    require(".." not in selected.split(os.sep), "parent traversal in source-root", 2)
    path = os.path.abspath(os.path.join(cwd, selected))
    require(sys.platform.startswith(("linux", "android")),
            "source locality admission requires Linux or Android", 78)
    # Read kernel metadata, never stat a remote target to determine locality.
    with open("/proc/self/mountinfo", "rb") as stream:
        raw = stream.read(MAX_MANIFEST + 1)
    require(len(raw) <= MAX_MANIFEST, "mount table exceeds admission bound", 78)
    mounts = []
    for line in raw.decode().splitlines():
        left, right = line.split(" - ", 1)
        mount = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), left.split()[4])
        mounts.append((mount, right.split()[0]))
    covering = [(m, fs) for m, fs in mounts if path == m or path.startswith(m.rstrip("/") + "/")]
    require(bool(covering), "unknown source filesystem", 78)
    require(max(covering, key=lambda item: len(item[0]))[1] in LOCAL_FS,
            "source-root is not on an admitted local filesystem", 78)
    require(not any(m.startswith(path.rstrip("/") + "/") for m, _ in mounts),
            "source-root contains nested mounts", 78)
    return path


def open_root(path):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open("/", flags)
    try:
        for component in path.split("/"):
            if component:
                child = os.open(component, flags, dir_fd=fd)
                os.close(fd)
                fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_source(fd, name):
    with os.fdopen(os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                           dir_fd=fd), "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode), f"nonregular source: {name!r}")
        require(before.st_size <= MAX_FILE, f"oversized source: {name!r}")
        content = stream.read(MAX_FILE + 1)
        after = os.fstat(stream.fileno())
    require(len(content) == before.st_size and len(content) <= MAX_FILE,
            f"source size changed: {name!r}")
    require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_size, after.st_mtime_ns, after.st_ctime_ns), f"source changed: {name!r}")
    return content


def snapshot(root, cwd):
    try:
        path = local_root(root, cwd)
        fd = open_root(path)
        try:
            names = []
            with os.scandir(fd) as entries:
                for count, entry in enumerate(entries, 1):
                    require(count <= MAX_FILES * 4, "too many source-root entries")
                    if entry.name.endswith(".org") and entry.name not in EXCLUDED and not entry.name.startswith("agents-skills"):
                        require(admitted(entry.name), "invalid root Org name")
                        names.append(entry.name)
            require(0 < len(names) <= MAX_FILES, "empty or oversized source admission")
            records, contents, total = [], [], 0
            for name in sorted(names, key=lambda n: (n.lower(), n)):
                content = read_source(fd, name)
                total += len(content)
                require(total <= MAX_CONTENT, "source content exceeds bound")
                records.append({"path": name, "bytes": len(content),
                                "sha256": hashlib.sha256(content).hexdigest()})
                contents.append(content)
        finally:
            os.close(fd)
        manifest = {"protocol": PROTOCOL, "admission": ADMISSION,
                    "source": {"host": socket.gethostname(), "checkout": path, "mode": "working-tree"},
                    "files": records}
        header = canonical(manifest)
        require(len(header) <= MAX_MANIFEST, "manifest exceeds bound")
        body = MAGIC + len(header).to_bytes(8, "big") + header + b"".join(contents)
        return body + hashlib.sha256(body).digest()
    except (OSError, UnicodeError, ValueError) as exc:
        raise Refusal(f"source capture refused: {exc}") from exc


def decode_frame(stream):
    frame = stream.read(MAX_FRAME + 1)
    require(len(frame) <= MAX_FRAME, "frame exceeds bound")
    prefix = len(MAGIC) + 8
    require(len(frame) >= prefix + 32 and frame.startswith(MAGIC), "invalid frame protocol", 78)
    size = int.from_bytes(frame[len(MAGIC):prefix], "big")
    require(0 < size <= MAX_MANIFEST and prefix + size + 32 <= len(frame), "invalid/truncated manifest")
    header = frame[prefix:prefix + size]
    try:
        manifest = json.loads(header)
        require(canonical(manifest) == header, "manifest is not canonical JSON")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Refusal("invalid manifest JSON") from exc
    require(isinstance(manifest, dict) and set(manifest) == {"protocol", "admission", "source", "files"},
            "unknown manifest fields")
    require(manifest["protocol"] == PROTOCOL and manifest["admission"] == ADMISSION,
            "unsupported snapshot protocol/admission", 78)
    source = manifest["source"]
    require(isinstance(source, dict) and set(source) == {"host", "checkout", "mode"}, "invalid source identity")
    require(all(isinstance(v, str) and v and "\x00" not in v and len(v) <= 4096 for v in source.values()),
            "invalid source identity values")
    require(source["mode"] == "working-tree" and source["checkout"].startswith("/")
            and ".." not in source["checkout"].split("/"), "invalid checkout identity")
    records = manifest["files"]
    require(isinstance(records, list) and 0 < len(records) <= MAX_FILES, "invalid file count")
    position, total, names, contents = prefix + size, 0, [], []
    for record in records:
        require(isinstance(record, dict) and set(record) == {"path", "bytes", "sha256"}, "invalid file record")
        try:
            valid_name = admitted(record["path"])
        except UnicodeError:
            valid_name = False
        require(valid_name, "unadmitted file path")
        count = record["bytes"]
        require(type(count) is int and 0 <= count <= MAX_FILE, "invalid file size")
        total += count
        require(total <= MAX_CONTENT and position + count <= len(frame) - 32, "truncated/oversized content")
        content = frame[position:position + count]
        require(hashlib.sha256(content).hexdigest() == record["sha256"], "file integrity failure")
        position += count
        names.append(record["path"])
        contents.append((record, content))
    require(names == sorted(set(names), key=lambda n: (n.lower(), n)), "duplicate/unsorted paths")
    require(position == len(frame) - 32, "trailing/truncated frame content")
    require(hashlib.sha256(frame[:-32]).digest() == frame[-32:], "frame integrity failure")
    return manifest, contents, frame


def envelope(payload):
    require(isinstance(payload, dict) and set(payload) ==
            {"protocol", "tool", "tool_dir", "argv", "caller_pwd", "router_stack"},
            "invalid invocation fields", 78)
    require(payload["protocol"] == PROTOCOL, "unsupported invocation protocol", 78)
    for key in ("tool", "tool_dir", "caller_pwd", "router_stack"):
        require(isinstance(payload[key], str) and payload[key] and "\x00" not in payload[key],
                "invalid invocation identity", 78)
    hub_real(payload["tool_dir"], payload["tool"])
    require(payload["caller_pwd"].startswith("/"), "caller_pwd must be absolute", 78)
    require(payload["router_stack"].split(":").count(payload["tool"]) == 1, "invalid recursion stack", 125)
    route, _ = classify(payload["argv"])
    require(route == "client-fanout-reconcile", "receiver requires source invocation", 78)
    data = canonical(payload)
    require(len(data) <= MAX_ENVELOPE, "invocation exceeds bound", 78)
    return base64.b64encode(data).decode("ascii")


def run_bounded(argv, frame, **kwargs):
    try:
        result = subprocess.run(argv, input=frame, timeout=SECONDS, **kwargs)
        return result.returncode if result.returncode >= 0 else 128 - result.returncode
    except subprocess.TimeoutExpired as exc:
        raise Refusal("reconcile deadline exceeded", 124) from exc
    except OSError as exc:
        raise Refusal(f"reconcile execution failed: {exc}", 127) from exc


def hub_real(tool_dir, tool):
    require(isinstance(tool_dir, str) and tool_dir in TOOL_DIRS,
            "unadmitted HelmCortex tool directory", 78)
    try:
        valid_tool = (isinstance(tool, str) and bool(tool) and tool not in {".", ".."}
                      and "/" not in tool and "\\" not in tool and "\x00" not in tool
                      and len(tool.encode("utf-8")) <= 255)
    except UnicodeError:
        valid_tool = False
    require(valid_tool, "invalid HelmCortex tool name", 78)
    return os.path.join(os.path.expanduser("~/HelmCortex"), tool_dir, tool)


def finalize(payload, stream, local_real=None):
    envelope(payload)
    _, _, frame = decode_frame(stream)
    env = os.environ.copy()
    env["HX_CALLER_PWD"] = payload["caller_pwd"]
    env["HX_ROUTER_STACK"] = payload["router_stack"]
    real = local_real if local_real is not None else hub_real(payload["tool_dir"], payload["tool"])
    return run_bounded([real, "hub-finalize", "--snapshot-protocol", PROTOCOL,
                        "--", *payload["argv"]], frame,
                       cwd=os.path.dirname(real), env=env)


def receive(encoded):
    def expired(signum, current):
        raise Refusal("receiver deadline exceeded", 124)
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(SECONDS)
    try:
        require(len(encoded) <= 4 * ((MAX_ENVELOPE + 2) // 3), "invocation exceeds bound", 78)
        try:
            payload = json.loads(base64.b64decode(encoded, validate=True))
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise Refusal("invalid invocation encoding", 78) from exc
        require(envelope(payload) == encoded, "noncanonical invocation encoding", 78)
        status = finalize(payload, sys.stdin.buffer)
    except Refusal as exc:
        print(f"hx-reconcile: {exc}", file=sys.stderr)
        status = exc.code
    finally:
        signal.alarm(0)
    raise SystemExit(status)


def dispatch(transport, tool, argv, root, local_real, tool_dir, stack, local, ssh):
    caller = os.environ.get("HX_CALLER_PWD", os.getcwd())
    payload = {"protocol": PROTOCOL, "tool": tool, "tool_dir": tool_dir, "argv": argv,
               "caller_pwd": caller, "router_stack": stack}
    encoded = envelope(payload)
    alias = transport.get("hub_ssh_alias")
    require(isinstance(alias, str) and alias and not alias.startswith("-"), "invalid hub alias", 78)
    options = transport.get("ssh_options", {})
    required = {"BatchMode": "yes", "PasswordAuthentication": "no",
                "KbdInteractiveAuthentication": "no", "PreferredAuthentications": "publickey",
                "ConnectTimeout": "10", "ConnectionAttempts": "1"}
    require(options == required and transport.get("kind") == "ssh-exec", "unsupported reconcile transport", 78)
    frame = snapshot(root, caller)
    if local:
        return finalize(payload, io.BytesIO(frame), local_real=local_real)
    code = ('import os,sys;sys.dont_write_bytecode=True;'
            'sys.path.insert(0,os.path.expanduser("~/.local/libexec"));'
            'import hx_reconcile;hx_reconcile.receive(sys.argv[1])')
    command = "python3 -c " + shlex.quote(code) + " " + shlex.quote(encoded)
    ssh_options = [item for key, value in required.items() for item in ("-o", f"{key}={value}")]
    return run_bounded([ssh, "-T", *ssh_options, alias, command], frame)
