#!/usr/bin/env python3
"""R2D2 pre_tool_call hook — checks Aura's tool calls BEFORE they run.

1. memory_fixer: a malformed built-in `memory` call (missing action / old_text /
   content) is stopped with the exact fix, instead of failing and looping.
2. write_guard, wrong capitals: writing into a folder that doesn't exist when one
   with different capitals does ("reports" vs "Reports") is stopped with the real path.
3. write_guard, clinical destination: copying/moving/extracting OUT of the Secret
   Vault, or writing text R2D2 judges clinical, to anywhere outside the Secret
   Vault is paused once (a speed bump, not a wall). The identical call retried
   within 15 minutes goes through: that is how Aura proceeds when the operator really
   asked for that location.
4. path_fixer: an image / video / file path that doesn't exist (e.g. a web-UI
   attachment with the session folder merged into the file name) is rewritten to
   the ONE clear match in this session's attachments or the same folder (pathfix.py).

Always prints valid JSON and exits 0; any internal error lets the call through
(fail open). Modes (active/shadow/off) come from ~/.hermes/r2d2/config.json.
Built 2026-09-29 by Honey Badger (Claude) for Mètsàtron.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))  # not .resolve(): the live file is a symlink into DotCortex
import r2d2lib as R  # noqa: E402
import pathfix  # noqa: E402

HOME = str(R.HOME)
VAULT = str(R.SECRET_VAULT)
BUMPS = R.STATE_DIR / "speed-bumps.json"
BUMP_WINDOW = 15 * 60
CLINICAL_Q = ("Is this a clinical note or record about a patient or client (their health, disability, care, "
              "assessment, diagnosis or an incident involving them)?")
CLINICAL_THRESH = 0.4   # benchmarked 2026-09-30: clean separation (non-clinical <= 0.23, clinical >= 0.64)


def out(obj=None):
    print(json.dumps(obj or {}))
    sys.exit(0)


def block(feature: str, message: str, **logf):
    R.log(feature, action="block" if R.mode(feature) == "active" else "would_block", **logf)
    if R.mode(feature) == "active":
        out({"action": "block", "message": f"[R2D2] {message}"})
    out()


# ----------------------------------------------------------------- memory tool
def check_memory(args: dict):
    if R.mode("memory_fixer") == "off":
        return
    ops = args.get("operations")
    if isinstance(ops, list) and ops:
        items = ops
    else:
        items = [args]
    for i, op in enumerate(items, 1):
        if not isinstance(op, dict):
            continue
        act = op.get("action")
        where = f"operation {i}: " if len(items) > 1 else ""
        if act not in ("add", "replace", "remove"):
            block("memory_fixer",
                  f"{where}`action` is missing or invalid ({act!r}). Use exactly one of "
                  "\"add\", \"replace\", \"remove\". Easier and with no size limit: "
                  "`aura-brain memory remember \"...\"` in your terminal.", reason="bad_action")
        if act in ("replace", "remove") and not (op.get("old_text") or "").strip():
            block("memory_fixer",
                  f"{where}`{act}` needs `old_text`: a short, exact snippet copied from the entry you mean. "
                  "Do one entry per call rather than a batch.", reason="no_old_text")
        if act in ("add", "replace") and not (op.get("content") or "").strip():
            block("memory_fixer",
                  f"{where}`{act}` needs `content`: the new text. To delete an entry use action \"remove\".",
                  reason="no_content")


# --------------------------------------------------------- destination parsing
SEP = re.compile(r"\s*(?:&&|\|\||;|\n)\s*")


def norm(p: str, cwd: str | None = None) -> str | None:
    p = p.strip().strip('"\'')
    if not p or p.startswith("-") or p in ("/dev/null", "-"):
        return None
    p = os.path.expanduser(p.replace("$HOME", HOME))
    if not p.startswith("/"):
        if not cwd:
            return None
        p = os.path.join(cwd, p)
    return os.path.normpath(p)


UNKNOWN_CWD = "/nonexistent-r2d2-unknown-cwd"   # outside the vault on purpose: unknown = not proven safe


def shell_dests(cmd: str, cwd: str | None):
    """Best-effort destinations written by a shell command. Tracks `cd DIR` in the chain;
    archive extraction with no explicit destination writes into the current folder."""
    dests = []
    here = cwd
    for part in SEP.split(cmd):
        for seg in part.split("|"):
            try:
                tok = shlex.split(seg, posix=True)
            except ValueError:
                continue
            if not tok:
                continue
            # redirections
            for i, t in enumerate(tok):
                if t in (">", ">>") and i + 1 < len(tok):
                    dests.append(tok[i + 1])
                elif re.match(r"^\d?>>?[^>&]", t):
                    dests.append(re.sub(r"^\d?>>?", "", t))
            prog = os.path.basename(tok[0])
            args = [t for t in tok[1:] if t not in (">", ">>")]
            if prog in ("cd", "pushd") and args:
                here = norm(args[0], here) or here
                continue
            extracting = (prog in ("unzip", "bsdtar") or
                          (prog == "tar" and any(re.match(r"^-?[a-zA-Z]*x", a) for a in args[:1])) or
                          (prog in ("7z", "7za") and args[:1] in (["x"], ["e"])))
            has_dest = (("-d" in args) if prog == "unzip" else
                        ("-C" in args) if prog in ("tar", "bsdtar") else
                        any(a.startswith("-o") for a in args))
            if extracting and not has_dest:
                dests.append(here or UNKNOWN_CWD)
            if prog in ("cp", "mv", "rsync", "install", "ln"):
                if "-t" in args and args.index("-t") + 1 < len(args):
                    dests.append(args[args.index("-t") + 1])
                else:
                    pos = [a for a in args if not a.startswith("-")]
                    if len(pos) >= 2:
                        dests.append(pos[-1])
            elif prog == "unzip" and "-d" in args and args.index("-d") + 1 < len(args):
                dests.append(args[args.index("-d") + 1])
            elif prog == "tar" and "-C" in args and args.index("-C") + 1 < len(args):
                dests.append(args[args.index("-C") + 1])
            elif prog in ("7z", "7za"):
                dests += [a[2:] for a in args if a.startswith("-o")]
            elif prog in ("tee", "touch", "mkdir"):
                dests += [a for a in args if not a.startswith("-")]
    out_ = [d for d in (norm(x, here) if not x.startswith("/") else os.path.normpath(x) for x in dests) if d]
    # 2026-10-11: `2>/dev/null` etc. are not destinations (paused Aura's read-only vault checks)
    return [d for d in out_ if not d.startswith(("/dev/", "/proc/"))]


def code_dests(code: str):
    dests = re.findall(r"open\(\s*[rRbBfF]?['\"]([^'\"]+)['\"]\s*,\s*['\"][wax]", code)
    dests += re.findall(r"shutil\.(?:copy\w*|move)\([^,]+,\s*[rRfF]?['\"]([^'\"]+)['\"]", code)
    dests += re.findall(r"(?:Path|os\.makedirs|os\.mkdir)\(\s*[rRfF]?['\"]([^'\"]+)['\"]\s*\)?\s*"
                        r"(?:\.(?:write_text|write_bytes|mkdir)|,|\))", code)
    for m in re.findall(r"subprocess\.\w+\(\s*\[([^\]]+)\]", code):
        dests += shell_dests(" ".join(x.strip().strip("'\"") for x in m.split(",")), None)
    return [d for d in (norm(x, None) for x in dests) if d]


def patch_dests(args: dict):
    d = [args.get("path") or ""]
    d += re.findall(r"^\*\*\* (?:Add|Update) File: (.+)$|^\*\*\* Move to: (.+)$", args.get("patch") or "", re.M)
    flat = []
    for x in d:
        if isinstance(x, tuple):
            flat += [y for y in x if y]
        elif x:
            flat.append(x)
    return [p for p in (norm(x, None) for x in flat) if p]


# ------------------------------------------------------------- wrong paths
def path_form_class(raw):
    """Classify notation only; never return path text or a content-derived ID."""
    if not isinstance(raw, str) or not raw.strip():
        return "invalid"
    value = raw.strip()
    if value.startswith(('"', "'")):
        return "quoted"
    if re.search(r"%[0-9A-Fa-f]{2}", value):
        return "percent_encoded"
    if value.startswith("file://"):
        return "file_uri"
    if re.match(r"^(https?|data|ftp):", value, re.I):
        return "unsupported_url"
    return "bare_absolute" if value.startswith("/") else "relative"


def log_path_diagnostic(raw, tool, directive, normalized_exists):
    """Only enum labels and a boolean; deliberately no session, name or path."""
    R.log("path_diagnostic", tool=tool, form_class=path_form_class(raw),
          directive=directive, normalized_exists=bool(normalized_exists))


def resolve_missing(sid: str, path: str):
    """read_file's decision for a path that does not exist, shared with the execute_code /
    terminal literal check. Returns ("fix", fixed_path, reason, n), ("block", message,
    reason, n) or ("none", None, reason, n). Pure: no logging, no output."""
    rooted = pathfix.home_rooted(path)     # Filebrowser-style '/Secret Vault/...'
    if rooted:
        path = rooted
    if rooted and os.path.exists(path):
        return "fix", path, "home_rooted", 1
    fixed, reason, n = pathfix.find_match(path, sid)
    if fixed:
        return "fix", fixed, reason, n
    folder, names = pathfix.suggestions(path)
    if not names:
        return "none", None, reason, n
    base = os.path.basename(path)
    # Ambiguous among near-identical siblings (e.g. three copies of one client's
    # report): show just that short, numbered cluster so the right one is obvious and
    # copyable, instead of a 15-line folder dump.
    cluster = pathfix.close_matches(path) if reason == "ambiguous" else []
    if len(cluster) >= 2:
        return ("block", f"The exact filename `{base}` does not exist — this is a name mismatch, NOT a "
                f"permissions or Secret-Vault block and not a broken PDF/Word reader (nothing was read). "
                f"{len(cluster)} files match it and they are DIFFERENT documents (the size and date after the "
                f"` · ` tell them apart):\n" +
                "\n".join(f"{i + 1}. {nm}" for i, nm in enumerate(cluster)) +
                "\nIf you were given a full file path, read that path verbatim. Otherwise pick the one you need, "
                "copy its name (everything before the ` · `) character-for-character, and read that — or ask which "
                "one is meant. Do not guess and do not say the vault blocked you — it didn't.",
                "ambiguous_client", len(cluster))
    # No single clear match: show what is really in the folder so she picks a real name.
    return ("block", f"That file does not exist — this is a wrong filename, NOT a permissions or "
            f"Secret-Vault block and not a broken PDF/Word reader (nothing was read). The vault is open "
            f"to you here; you just named a file that isn't there. What is really in `{folder}`:\n- " +
            "\n- ".join(names) +
            "\nEach line is a real file; the size and date after the ` · ` tell near-identical names apart. "
            "Pick the one you need, copy the name (everything before the ` · `) character-for-character, and "
            "read that. If you were given a full file path, read that path verbatim. "
            "Do not tell anyone the vault blocked you — it didn't.",
            "suggest_" + reason, n)


def check_paths(sid: str, tool: str, args: dict, cwd: str | None):
    """Rewrite a non-existent path to its one clear match. Logs labels only, never paths."""
    if R.mode("path_fixer") == "off" or tool not in pathfix.PATH_ARGS:
        return
    key = pathfix.PATH_ARGS[tool]
    raw = args.get(key)
    path = pathfix.local_path(raw, cwd)
    if not path:
        log_path_diagnostic(raw, tool, "none", False)
        return
    if os.path.exists(path):
        # Normalize only copy/paste syntax that the public reader does not
        # accept. Bare paths keep their exact reader semantics, including
        # symlink/parent traversal and leading double slashes.
        raw_s = raw.strip() if isinstance(raw, str) else ""
        syntax = raw_s.strip("\"'")
        syntax_changed = (raw_s != raw or raw_s.startswith(("\"", "'")) or
                          syntax.startswith("file://"))
        if syntax_changed:
            if syntax.startswith("file://"):
                syntax = syntax[7:]
            syntax = os.path.expanduser(syntax)
            if not syntax.startswith("/") and cwd:
                syntax = os.path.join(cwd, syntax)
            # Only rewrite when the syntax-stripped reader target is the same
            # semantic target as pathfix's normalized existing path.
            safe = syntax.startswith("/") and os.path.realpath(syntax) == os.path.realpath(path)
            if safe:
                active = R.mode("path_fixer") == "active"
                R.log("path_fixer", action="fix" if active else "would_fix",
                      tool=tool, reason="normalize", n_candidates=0)
                if active:
                    log_path_diagnostic(raw, tool, "modify", True)
                    out({"action": "modify", "args": {key: path}})
        log_path_diagnostic(raw, tool, "none", True)
        return
    kind, fixed, reason, n = resolve_missing(sid, path)
    if kind == "none":
        R.log("path_fixer", action="none", tool=tool, reason=reason, n_candidates=n)
        log_path_diagnostic(raw, tool, "none", False)
        return
    if kind == "block":
        # These blocks are R2D2 STEERING Aura, not the tool failing. Mark them so the
        # post_tool hook doesn't count them toward the consecutive-failure wall and lock
        # read_file after 3 (the recurring "Aura can't read the report", 2026-10-20).
        R.mark_steer(sid, tool)
        log_path_diagnostic(raw, tool, "block" if R.mode("path_fixer") == "active" else "none", False)
        block("path_fixer", fixed, reason=reason, tool=tool, n_candidates=n)
    active = R.mode("path_fixer") == "active"
    R.log("path_fixer", action="fix" if active else "would_fix", tool=tool, reason=reason, n_candidates=n)
    log_path_diagnostic(raw, tool, "modify" if active else "none", False)
    if active:
        out({"action": "modify", "args": {key: fixed}})


# ---------------------------------------------- shell path slips (terminal)
QUOTED_TILDE = re.compile(r"""(["'])~/""")
QUOTED_ROOTED = re.compile(r"""(["'])/(Secret Vault|Obsidian Vault|Documents|HEEA)/""")


def fix_terminal_paths(command: str):
    """'~/…' inside quotes is never expanded by the shell, and Filebrowser shows home as '/'.
    Returns the corrected command, or None. Logs labels only."""
    if R.mode("path_fixer") == "off" or not command:
        return None
    new = QUOTED_TILDE.sub(lambda m: m.group(1) + HOME + "/", command)
    new = QUOTED_ROOTED.sub(lambda m: m.group(1) + HOME + "/" + m.group(2) + "/", new)
    if new == command:
        return None
    active = R.mode("path_fixer") == "active"
    R.log("path_fixer", action="fix" if active else "would_fix", tool="terminal", reason="shell_quoting")
    return new if active else None


# ------------------------- file paths READ by execute_code / terminal (2026-11-26)
# Aura also opens documents from execute_code and terminal, and those paths were never
# checked: a misnamed file failed as a bare "No such file" and she went round in circles
# ("R2D2 confirmed it's on disk but the path fails"). Only a path the call clearly READS is
# checked: a missing OUTPUT path is a file about to be created and must never be retargeted
# onto an existing document. The decision is read_file's (resolve_missing): one clear match
# rewrites just that literal; ambiguous / no match blocks with the same pick-list. Existing
# paths are untouched. Anything unparseable or unexpected lets the call through unchanged.
LIT_ROOTED = re.compile(r"^/(Secret Vault|Obsidian Vault|Documents|HEEA)/")
LIT_SKIP = re.compile(r"[*?{}\x00-\x1f]|%[sdr(]")       # globs, templates, control chars
MAX_LITERALS = 12
PATH_KW = {"file", "filename", "path", "fp", "docx", "stream", "filepath", "fname", "src", "source", "input"}
SAME_PATH = {"Path", "PurePath", "PosixPath", "str", "expanduser", "abspath", "normpath", "realpath", "fspath"}
READ_FIRST = {"open", "Document", "load_workbook", "PdfReader", "PdfFileReader", "PdfDocument", "ZipFile",
              "convert_from_path", "extract_text", "copy", "copy2", "copyfile", "copyfileobj"}
WRITE_CALLS = {"save", "write_text", "write_bytes", "mkdir", "makedirs", "touch", "move", "copytree", "rmtree",
               "remove", "unlink", "rmdir", "savefig", "output", "dump", "write", "writelines", "extractall",
               "extract", "symlink_to", "hardlink_to", "link", "symlink", "to_csv", "to_excel", "to_json",
               "to_parquet", "to_html", "to_markdown", "to_pickle", "copy", "copy2", "copyfile"}
# terminal programs, by which arguments they only READ
READ_ALL = {"cat", "less", "more", "head", "tail", "file", "stat", "wc", "ls", "md5sum", "sha1sum", "sha256sum",
            "sha512sum", "strings", "xxd", "hexdump", "od", "pdfinfo", "pdffonts", "identify", "mediainfo",
            "readlink", "realpath", "zipinfo", "antiword", "catdoc", "xdg-open", "test", "["}
READ_FIRST_ARG = {"pdftotext", "pdftoppm", "pdftohtml", "pdftocairo", "pdfimages", "docx2txt", "unzip",
                  "tesseract", "ocrmypdf"}
READ_BUT_OUT = {"pandoc": {"-o", "--output"}, "libreoffice": {"--outdir"}, "soffice": {"--outdir"},
                "lowriter": {"--outdir"}}
WRAPPERS = {"sudo", "nice", "nohup", "command", "exec", "time", "env"}
PASSIVE = READ_ALL | {"cd", "echo", "printf", "true", "false", ":", "pwd"}   # create nothing
PRODUCERS = WRITE_CALLS | {"convert", "convert_file", "convert_text", "export", "system", "run", "call",
                           "check_output", "check_call", "Popen", "urlretrieve", "download"}
OUT_OPTS = {"-o", "-O", "-d", "--output", "--outdir", "--sidecar"}   # the next word is an output


def literal_path(value):
    """(raw, normalized) when value is plainly a document path in the home folder, else None."""
    if (not isinstance(value, str) or not value or len(value) > 1024 or value != value.strip()
            or LIT_SKIP.search(value)):
        return None
    if not (value.startswith(("~/", HOME + "/")) or LIT_ROOTED.match(value)):
        return None
    if value.endswith("/") or not os.path.splitext(os.path.basename(value))[1]:
        return None     # folders and extension-less names are not a document read
    path = pathfix.local_path(value, None)
    return (value, path) if path else None


def literal_decision(sid: str, value: str, path: str, expand_tilde: bool = False):
    """resolve_missing for one literal. With expand_tilde (Python code, whose open() never
    expands '~'), an existing '~/' literal becomes the absolute path; any other existing
    path is left exactly as written."""
    if os.path.exists(path):
        if expand_tilde and value.startswith("~/"):
            return "fix", path, "tilde", 0
        return "exists", None, "exists", 0
    return resolve_missing(sid, path)


def _callee(node):
    f = node.func
    if isinstance(f, ast.Name):
        return None, f.id
    if isinstance(f, ast.Attribute):
        o = f.value
        return (o.id if isinstance(o, ast.Name) else o.attr if isinstance(o, ast.Attribute) else None), f.attr
    return None, None


def _read_mode(node, pos: int) -> bool:
    """open()/ZipFile() mode is read-only (absent, or a constant without w/a/x/+)."""
    mode = node.args[pos] if len(node.args) > pos else next(
        (k.value for k in node.keywords if k.arg == "mode"), None)
    if mode is None:
        return True
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and not re.search(r"[wax+]", mode.value)


def code_read_literals(code: str):
    """{literal_node: (raw, path)} for string literals in Python code that are clearly opened
    for READING and never written. Raises SyntaxError for code that doesn't parse."""
    tree = ast.parse(code)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    lits = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            par = parents.get(node)
            if isinstance(par, (ast.JoinedStr, ast.BinOp)) or (
                    isinstance(par, ast.Attribute) and par.attr in ("format", "join")):
                continue    # a piece of a bigger path/template, not a whole path
            lp = literal_path(node.value)
            if lp:
                lits[node] = lp
    if not lits:
        return {}
    taint = {}     # variable name -> literal nodes it holds unchanged

    def refs(e):
        if isinstance(e, ast.Constant):
            return {e} if e in lits else set()
        if isinstance(e, ast.Name):
            return set(taint.get(e.id, ()))
        if isinstance(e, ast.Call):
            owner, name = _callee(e)
            if name in SAME_PATH and e.args:
                return refs(e.args[0])
            if name in ("expanduser", "resolve", "absolute") and isinstance(e.func, ast.Attribute) and not e.args:
                return refs(e.func.value)
        return set()

    def bind(target, found):
        if isinstance(target, ast.Name) and found:
            if not found <= taint.get(target.id, set()):
                taint.setdefault(target.id, set()).update(found)
                return True
        elif isinstance(target, (ast.Tuple, ast.List)):
            return any([bind(t, found) for t in target.elts])
        return False

    for _ in range(4):      # small fixpoint over simple assignments / loops
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and node.value is not None:
                for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                    changed |= bind(t, refs(node.value))
            elif isinstance(node, (ast.For, ast.comprehension)) and isinstance(node.iter, (ast.List, ast.Tuple)):
                found = set().union(*[refs(x) for x in node.iter.elts]) if node.iter.elts else set()
                changed |= bind(node.target, found)
            elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                changed |= bind(node.optional_vars, refs(node.context_expr))
        if not changed:
            break

    def anywhere(e):
        found = set()
        for x in ast.walk(e):
            found |= refs(x) if isinstance(x, (ast.Constant, ast.Name)) else set()
        return found

    reads, writes, producers = [], set(), []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        owner, name = _callee(node)
        here = (node.lineno, node.col_offset)
        args = list(node.args)
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        first = args[0] if args else next((kw[k] for k in PATH_KW if k in kw), None)
        # reads: the path is the call's first / named file argument
        if first is not None and (name in READ_FIRST or (name or "").startswith("read_") or
                                  (name == "process" and owner in ("docx2txt", "textract"))):
            if name not in ("open", "ZipFile") or _read_mode(node, 1):
                reads.append((here, refs(first)))
        if isinstance(node.func, ast.Attribute) and name in ("read_text", "read_bytes", "open"):
            if name != "open" or _read_mode(node, 0):
                reads.append((here, refs(node.func.value)))
        passive = False
        if name in ("run", "call", "check_output", "check_call", "Popen") and args and \
                isinstance(args[0], (ast.List, ast.Tuple)):
            argv = [x.value if isinstance(x, ast.Constant) and isinstance(x.value, str) else None
                    for x in args[0].elts]
            idx = argv_reads(argv)
            for i in idx:
                reads.append((here, refs(args[0].elts[i])))
            for j, x in enumerate(args[0].elts):
                if j not in idx:
                    writes |= refs(x)
            passive = _prog(argv)[1] in PASSIVE
        # something that may CREATE files: a read after it may be of its output
        if (name in PRODUCERS and not passive) or (name in ("open", "ZipFile") and not _read_mode(node, 1)):
            producers.append(here)
        # writes: anything inside a writing call (copy*: everything but the source)
        if name in WRITE_CALLS:
            pieces = args[1:] + [v for k, v in kw.items() if k not in PATH_KW] if name.startswith("copy") \
                else args + list(kw.values())
            for x in pieces:
                writes |= anywhere(x)
            if isinstance(node.func, ast.Attribute) and not name.startswith("copy"):
                writes |= anywhere(node.func.value)
        if name in ("replace", "rename") and (owner in ("os", "shutil") or (
                isinstance(node.func, ast.Attribute) and refs(node.func.value))):
            for x in args + [node.func.value]:
                writes |= anywhere(x)
        if name in ("open", "ZipFile") and not _read_mode(node, 1):
            for x in args[:1] + [kw[k] for k in PATH_KW if k in kw]:
                writes |= anywhere(x)
        if name == "open" and isinstance(node.func, ast.Attribute) and not _read_mode(node, 0):
            writes |= anywhere(node.func.value)
    written = {lits[n][1] for n in writes}
    first_producer = min(producers) if producers else None
    found = {}
    for pos, nodes in reads:
        if first_producer is None or pos <= first_producer:     # straight-line order
            for n in nodes:
                if lits[n][1] not in written:
                    found[n] = lits[n]
    return found


def shell_words(cmd: str):
    """Commands as lists of words {text, start, end, quote, redirect}, or None when the command
    is too dynamic to analyse (substitution, heredoc, unterminated quote). quote is "'" or '"'
    for one fully quoted word, "" for a plain unquoted word, None when it can't be rewritten."""
    if "`" in cmd or "$(" in cmd or "<<" in cmd:
        return None
    cmds, cur, i, n, redirect = [], [], 0, len(cmd), None
    stops = " \t;&|()\n<>"
    while i < n:
        c = cmd[i]
        if c in " \t":
            i += 1
            continue
        if c in stops:
            j = i
            while j < n and cmd[j] in stops[2:]:
                j += 1
            op = cmd[i:j]
            if "<" in op or ">" in op:
                if re.search(r"[;|()\n]", op):
                    return None
                if cur and cur[-1]["end"] == i and cur[-1]["text"].isdigit() and cur[-1]["quote"] == "":
                    cur.pop()   # the '2' of '2>'
                redirect = "in" if op == "<" else "out"
            else:
                if cur:
                    cmds.append(cur)
                cur, redirect = [], None
            i = j
            continue
        start, text, kinds, ok = i, "", [], True
        while i < n and cmd[i] not in stops:
            c = cmd[i]
            if c == "'":
                j = cmd.find("'", i + 1)
                if j < 0:
                    return None
                text += cmd[i + 1:j]
                kinds.append("'")
                i = j + 1
            elif c == '"':
                j = i + 1
                while j < n and cmd[j] != '"':
                    j += 2 if cmd[j] == "\\" else 1
                if j >= n:
                    return None
                inner = cmd[i + 1:j]
                ok = ok and not re.search(r"[$`\\]", inner)
                text += inner
                kinds.append('"')
                i = j + 1
            else:
                j = i
                while j < n and cmd[j] not in stops and cmd[j] not in "'\"":
                    j += 2 if cmd[j] == "\\" else 1
                piece = cmd[i:j]
                ok = ok and not re.search(r"[$\\*?\[\]{}]", piece)
                text += piece
                kinds.append("")
                i = min(j, n)
        quote = kinds[0] if ok and len(kinds) == 1 else None
        cur.append({"text": text, "start": start, "end": i, "quote": quote, "redirect": redirect})
        redirect = None
    if cur:
        cmds.append(cur)
    return cmds


def _prog(words):
    """(index, program basename) of an argv after VAR=x / sudo / env / timeout N; (k, None)."""
    k = 0
    while k < len(words) and words[k] is not None and (
            words[k] in WRAPPERS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[k])):
        k += 1
    if k < len(words) and words[k] == "timeout":
        k += 2
    if k >= len(words) or words[k] is None:
        return k, None
    return k, os.path.basename(words[k])


def argv_reads(words):
    """Indexes of argv entries (None = not a constant) that the program only READS."""
    words = list(words)
    k, prog = _prog(words)
    if prog is None:
        return set()
    rest = [(i, w) for i, w in enumerate(words) if i > k]
    pathish = [(i, w) for i, w in rest if w is not None and w.startswith(("/", "~"))]
    if prog in READ_ALL:
        return {i for i, _ in pathish}
    if prog in READ_FIRST_ARG:
        inputs = [i for i, _ in pathish if words[i - 1] not in OUT_OPTS]
        return {inputs[0]} if inputs else set()
    if prog in ("cp", "rsync"):
        if any(w is not None and (w == "-t" or w.startswith("--target-directory")) for _, w in rest):
            return set()
        positional = [i for i, w in rest if w is None or not w.startswith("-")]
        return {i for i in positional[:-1] if i in dict(pathish)}
    if prog in READ_BUT_OUT:
        outs = READ_BUT_OUT[prog]
        return {i for i, _ in pathish if words[i - 1] not in outs}
    return set()


def terminal_read_words(cmd: str, workdir):
    """[(word, raw, path)] for quoted or simple words of `cmd` that a reader program only
    reads (or that feed a '<' redirect). None when the command can't be analysed."""
    cmds = shell_words(cmd)
    if cmds is None:
        return None
    dests = set(shell_dests(cmd, workdir))
    found = []
    for words in cmds:
        argv = [w for w in words if w["redirect"] is None]
        texts = [w["text"] for w in argv]
        idx = argv_reads(texts)
        picked = [argv[i] for i in idx] + [w for w in words if w["redirect"] == "in"]
        for w in picked:
            lp = literal_path(w["text"])
            if lp and lp[1] not in dests and w["quote"] is not None:
                found.append((w, lp[0], lp[1]))
        if _prog(texts)[1] not in PASSIVE or any(w["redirect"] == "out" for w in words):
            break   # this command may create files: later reads may be of its output
    return found


def _shell_quote(path: str, quote: str):
    """The word to put back, or None if `path` can't be written safely in that quoting."""
    if quote == '"':
        return None if re.search(r'["$`\\]', path) else '"' + path + '"'
    if quote == "'" or quote == "":
        return None if "'" in path else "'" + path + "'"
    return None


def literal_mode() -> str:
    """path_fixer's mode, unless config key "path_fixer_code" turns just this check down
    ("shadow" / "off"): a kill switch for the execute_code / terminal coverage alone."""
    base, own = R.mode("path_fixer"), R.config().get("path_fixer_code")
    if base == "off" or own == "off":
        return "off"
    return "shadow" if own == "shadow" else base


def check_literal_paths(sid: str, tool: str, args: dict):
    """execute_code / terminal: fix or steer document paths the call reads. Returns the
    args to modify ({"code": ...} / {"command": ...}) or None; may block (exits)."""
    if tool not in ("execute_code", "terminal"):
        return None
    try:
        lmode = literal_mode()
        if lmode == "off":
            return None
        if tool == "execute_code":
            code = args.get("code")
            if not isinstance(code, str) or not code:
                return None
            try:
                hits = [(node, raw, path) for node, (raw, path) in code_read_literals(code).items()]
            except (SyntaxError, ValueError, RecursionError):
                R.log("path_fixer", action="none", tool=tool, reason="parse_error", n_candidates=0)
                return None
        else:
            cmd = args.get("command")
            if not isinstance(cmd, str) or not cmd:
                return None
            hits = terminal_read_words(cmd, args.get("workdir"))
            if hits is None:
                return None
        active = lmode == "active"
        fixes, blocks = [], []
        for item, raw, path in hits[:MAX_LITERALS]:
            kind, value, reason, n = literal_decision(sid, raw, path, tool == "execute_code")
            if kind == "exists":
                continue
            if kind == "none":
                R.log("path_fixer", action="none", tool=tool, reason=reason, n_candidates=n)
            elif kind == "block":
                blocks.append((value, reason, n))
            else:
                fixes.append((item, value, reason, n))
        if blocks:
            message, reason, n = blocks[0]
            if len(blocks) > 1:
                message += f"\n({len(blocks)} file paths in this {tool} call don't exist; check each one.)"
            if active:
                R.mark_steer(sid, tool)     # steering, not a tool failure (see check_paths)
                block("path_fixer", message, reason=reason, tool=tool, n_candidates=n)
            R.log("path_fixer", action="would_block", tool=tool, reason=reason, n_candidates=n)
            return None
        if not fixes:
            return None
        for _, _, reason, n in fixes:
            R.log("path_fixer", action="fix" if active else "would_fix", tool=tool, reason=reason, n_candidates=n)
        if not active:
            return None
        if tool == "execute_code":
            data = code.encode("utf-8")
            starts = [0]
            for line in data.splitlines(keepends=True):
                starts.append(starts[-1] + len(line))
            spans = []
            for node, fixed, _, _ in fixes:
                a = starts[node.lineno - 1] + node.col_offset
                b = starts[node.end_lineno - 1] + node.end_col_offset
                spans.append((a, b, repr(fixed).encode("utf-8")))
            for a, b, rep in sorted(spans, reverse=True):
                data = data[:a] + rep + data[b:]
            new = data.decode("utf-8")
            ast.parse(new)      # never hand back code that no longer parses
            return {"code": new}
        new = cmd
        for word, fixed, _, _ in sorted(fixes, key=lambda f: f[0]["start"], reverse=True):
            rep = _shell_quote(fixed, word["quote"])
            if rep is None:
                R.log("path_fixer", action="none", tool=tool, reason="unquotable", n_candidates=0)
                return None
            new = new[:word["start"]] + rep + new[word["end"]:]
        return {"command": new}
    except SystemExit:
        raise
    except Exception:
        return None


# ------------------------------------------------------------------- checks
def inside_vault(p: str) -> bool:
    try:
        rp = os.path.realpath(p)
    except OSError:
        rp = p
    return rp == VAULT or rp.startswith(VAULT + "/") or p.startswith(VAULT + "/")


def case_fix(path: str):
    parts = Path(path).parts
    cur = Path(parts[0])
    changed = False
    for part in parts[1:]:
        nxt = cur / part
        if nxt.exists():
            cur = nxt
            continue
        try:
            opts = [c for c in os.listdir(cur) if c.lower() == part.lower()]
        except OSError:
            return None
        if len(opts) != 1:
            return str(cur / part) if changed else None  # rest is new
        cur = cur / opts[0]
        changed = True
    return str(cur) if changed else None


def short(p: str) -> str:
    if p == UNKNOWN_CWD:
        return "the current folder (in the web UI that is usually ~/workspace)"
    return "~" + p[len(HOME):] if p.startswith(HOME + "/") else p


def speed_bump(key: str) -> bool:
    """True if this exact call was already paused recently (so let it through now)."""
    try:
        bumps = json.loads(BUMPS.read_text()) if BUMPS.exists() else {}
    except Exception:
        bumps = {}
    now = time.time()
    bumps = {k: t for k, t in bumps.items() if now - t < BUMP_WINDOW}
    if key in bumps:
        bumps.pop(key)
        seen = True
    else:
        bumps[key] = now
        seen = False
    try:
        R.STATE_DIR.mkdir(parents=True, exist_ok=True)
        BUMPS.write_text(json.dumps(bumps))
        os.chmod(BUMPS, 0o600)
    except Exception:
        pass
    return seen


def check_writes(tool: str, args: dict, cwd: str | None):
    if R.mode("write_guard") == "off":
        return
    text = ""
    if tool == "write_file":
        dests = [p for p in [norm(args.get("path") or "", cwd)] if p]
        text = args.get("content") or ""
    elif tool == "patch":
        dests = patch_dests(args)
        text = (args.get("new_string") or "") + (args.get("patch") or "")
    elif tool == "terminal":
        cmd = args.get("command") or ""
        # the gateway's cwd is not the terminal's; only trust an explicit workdir
        dests = shell_dests(cmd, args.get("workdir"))
        text = cmd
    elif tool == "execute_code":
        code = args.get("code") or ""
        dests = code_dests(code)
        text = code
    else:
        return
    if not dests:
        return

    # (a) wrong capitals — deterministic
    for d in dests:
        if os.path.exists(d):
            continue
        fixed = case_fix(d)
        if fixed and fixed != d:
            block("write_guard", f"Wrong capitals: `{short(d)}` would create a new, duplicate folder. "
                  f"The existing folder is spelled `{short(fixed)}`. Use that path. "
                  "`aura-find check \"<path>\"` verifies any path.", reason="case_mismatch")

    outside = [d for d in dests if not inside_vault(d)]
    if not outside:
        return

    # (b) clinical leaving the vault
    from_vault = "Secret Vault" in text and tool in ("terminal", "execute_code")
    p_clin = None
    if not from_vault and tool in ("write_file", "patch") and len(text.strip()) > 80:
        p_clin = R.yes_prob(text[:3000], CLINICAL_Q, timeout=4)
    clinical = from_vault or (p_clin is not None and p_clin >= CLINICAL_THRESH)
    R.log("write_guard_scan", tool=tool, n_dests=len(dests), from_vault=from_vault,
          p_clinical=None if p_clin is None else round(p_clin, 3))
    if not clinical:
        return
    key = hashlib.sha256((tool + json.dumps(args, sort_keys=True)).encode()).hexdigest()
    if speed_bump(key):
        R.log("write_guard", action="override_retry", tool=tool)
        return
    why = "takes files out of the Secret Vault" if from_vault else \
        f"writes what looks like clinical content (R2D2 {p_clin:.0%} sure)"
    block("write_guard",
          f"Paused: this {why} into {', '.join('`' + short(d) + '`' for d in outside[:3])}, outside the "
          "Secret Vault. Clinical material belongs in `~/Secret Vault/` (client work under "
          "`~/Secret Vault/Reports/<client>/`). If the operator explicitly asked for this exact location, "
          "make the identical call again and it will go through. Otherwise write it inside the Secret Vault.",
          reason="clinical_outside_vault", tool=tool)


# ------------------------------------------------ vault block (Mètsàtron's chats)
# 2026-11-07: match PATH-SHAPED vault references, not the phrase. A boundary affirmation
# ("no clinical data; the Secret Vault stays closed") was being blocked as if it were a breach,
# which made a successful write look failed and drove a retry/confession loop.
VAULT_REF = re.compile(r"(?:~|/home/gille|/home)?/?(?:Secret[ _]Vault)(?:[/\\]|$)|secret\*", re.I)
SEARCHERS = re.compile(r"(^|[\s;|&(`$])(find|fd|fdfind|locate|plocate|tree|du|rg|ag|ncdu)\b|"
                       r"\b(e|f)?grep\s+(-\S+\s+)*-[a-zA-Z]*[rR]|\bls\s+(-\S+\s+)*-[a-zA-Z]*R|"
                       r"os\.walk|\.rglob\(|glob\.glob\(|\biglob\(")
HOME_ROOT = re.compile(r"(^|[\s'\"(=,])(~|\$HOME|/home/gille|/home|/)/?(\*)?(?=$|[\s'\")\],;|&])|"
                       r"Path\.home\(\)|expanduser\(\s*['\"]~/?['\"]\s*\)")
VAULT_CLOSED = ("In Mètsàtron's chats the Secret Vault stays closed: he isn't cleared for clinical material, "
                "so you can't open, list or search it here. You may tell him that the work exists and lives in "
                "the Secret Vault, but no client names, file names or contents. the operator can reach it from her "
                "own chat. If this is a file outside the vault that only mentions the vault path (a skill or a note), "
                "stop and ask Honey Badger to make that edit; don't look for another way round this block.")


def vault_block(tool: str, args: dict):
    """Only called for sessions identified as Mètsàtron's Telegram chat."""
    if R.mode("vault_block") == "off":
        return
    if tool in ("terminal", "execute_code"):
        text = args.get("command") or args.get("code") or ""
    elif tool in ("read_file", "write_file", "patch", "search_files", "list_directory", "send_message",
                  "vision_analyze", "text_to_speech"):
        text = json.dumps(args, ensure_ascii=False)
    else:
        return
    if VAULT_REF.search(text):
        block("vault_block", VAULT_CLOSED, reason="vault_ref", tool=tool)
    if tool in ("terminal", "execute_code") and SEARCHERS.search(text) and HOME_ROOT.search(text):
        block("vault_block", VAULT_CLOSED + " Whole-home searches would walk into it: search a narrower "
              "folder, or use `aura-find`, which skips the vault in his chats.", reason="home_search", tool=tool)
    if tool == "search_files":
        root = os.path.normpath(os.path.expanduser(str(args.get("path") or "~")))
        if root in (HOME, "/", "/home", "."):
            block("vault_block", VAULT_CLOSED + " Search a narrower folder than the whole home.",
                  reason="home_search", tool=tool)
    if tool == "terminal" and R.mode("vault_block") == "active" and "aura-find" in (args.get("command") or ""):
        # aura-find hides the vault when R2D2_NO_VAULT is set; a subshell keeps it out of shared shells
        R.log("vault_block", action="modify_aura_find")
        out({"action": "modify", "args": {"command": "(export R2D2_NO_VAULT=1\n" + args["command"] + "\n)"}})


# ------------------------------------------------------ risky commands
RISKY = [
    (re.compile(r"\b(rc-service|service|/etc/init\.d/)\s*(gille-llama-swap|identity-proxy)\b[^;&|\n]*\b(stop|restart|zap)\b"
                r"|\bpkill\b[^;&|\n]*\b(llama|llama-swap|identity)|\bkillall\s+(llama|llama-server|llama-swap)"),
     "this restarts or stops your own model stack (llama-swap / identity-proxy). That can take the whole system, "
     "you included, offline, and it doesn't always come back on its own. Those restarts go through Tiago"),
    (re.compile(r"\b(rc-service|service)\s*(hermes-gateway|hermes-webui)\b[^;&|\n]*\b(stop|restart|zap)\b|"
                r"\bhermes\s+gateway\s+(restart|stop)\b|\bpkill\b[^;&|\n]*hermes"),
     "this restarts or stops your own gateway, which ends this conversation mid-turn. `hermes gateway restart` "
     "mis-manages OpenRC here. Gateway restarts go through Tiago"),
    (re.compile(r"\brm\s+(-[a-zA-Z]*[rR][a-zA-Z]*\s+|--recursive\s+)+[^;&|\n]*"
                r"(Secret\\? ?Vault|Obsidian\\? ?Vault|~/?(\s|$)|/home/gille/?(\s|$)|\.hermes|/opt\b|Documents)"),
     "this recursively deletes inside an important area (a vault, Documents, ~/.hermes or your home)"),
    (re.compile(r"\b(chmod|chown)\s+-[a-zA-Z]*R[^;&|\n]*(~|/home/gille|Vault)"),
     "this recursively changes permissions on your home or a vault, which can lock the operator out of her files"),
]


def check_risky(tool: str, args: dict):
    if R.mode("risky") == "off" or tool not in ("terminal", "execute_code"):
        return
    text = args.get("command") or args.get("code") or ""
    for rx, why in RISKY:
        if rx.search(text):
            key = hashlib.sha256((tool + json.dumps(args, sort_keys=True)).encode()).hexdigest()
            if speed_bump(key):
                R.log("risky", action="override_retry")
                return
            block("risky", f"Paused: {why}. If Tiago or the operator explicitly asked for exactly this, make the "
                  "identical call again and it will run.", reason=RISKY.index((rx, why)))


# --------------------------------------------------- command not found
SHELL_WORDS = {"cd", "export", "source", ".", "echo", "printf", "test", "[", "[[", "if", "then", "else", "fi",
               "for", "while", "do", "done", "case", "esac", "set", "unset", "read", "true", "false", "exit",
               "return", "local", "eval", "exec", "time", "pushd", "popd", "alias", "type", "command", "builtin",
               "let", "declare", "shift", "trap", "wait", "ulimit", "umask", "{", "}", "(", ")", "!", "function",
               "select", "until", "history", "jobs", "fg", "bg", "kill", "hash", "help", "sudo", "nohup", "env",
               "nice", "timeout", "xargs"}
EXTRA_PATH = ["/home/gille/.local/bin", "/home/gille/.hermes/bin", "/home/gille/bin", "/usr/local/bin",
              "/usr/local/sbin", "/usr/sbin", "/sbin"]


def check_missing_commands(tool: str, args: dict):
    if R.mode("cmd_check") == "off" or tool != "terminal":
        return
    import shutil
    path = os.pathsep.join([os.environ.get("PATH", "/usr/bin:/bin")] + EXTRA_PATH)
    cmd = args.get("command") or ""
    if "<<" in cmd or "function " in cmd or "()" in cmd:   # heredocs / shell functions: too dynamic
        return
    for part in SEP.split(cmd):
        for seg in part.split("|"):
            try:
                tok = shlex.split(seg)
            except ValueError:
                return
            tok = [t for t in tok if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t)]   # VAR=x prefixes
            if not tok:
                continue
            w = tok[0]
            if w in SHELL_WORDS or "/" in w or w.startswith(("$", "`", "(")) or not re.match(r"^[\w.+-]+$", w):
                continue
            if shutil.which(w, path=path):
                continue
            key = "cmd:" + w
            if speed_bump(hashlib.sha256(key.encode()).hexdigest()):
                R.log("cmd_check", action="override_retry")
                return
            import difflib
            names = set()
            for d in path.split(os.pathsep):
                try:
                    names.update(os.listdir(d))
                except OSError:
                    pass
            near = difflib.get_close_matches(w, list(names), n=3, cutoff=0.75)
            hint = f" Did you mean: {', '.join('`' + n + '`' for n in near)}?" if near else ""
            block("cmd_check", f"`{w}` isn't installed or on the PATH here, so this would fail.{hint} "
                  "(If you're sure it exists, run the identical call again.)", reason="not_found")


# ---------------------------------------------------------- stuck loop
def args_key(tool: str, args) -> str:
    try:
        return hashlib.sha256((tool + json.dumps(args, sort_keys=True)).encode()).hexdigest()[:12]
    except Exception:
        return ""


def check_loop(sid: str, tool: str, args=None):
    if R.mode("loop_guard") == "off" or not sid:
        return
    streak = R.counter(sid, "fail_streak:" + tool)
    # 2026-10-11: only stop an exact repeat of a call that already failed (or a long streak);
    # corrected retries (e.g. a shorter description) go through
    repeat = R.counter(sid, "fail_args:" + args_key(tool, args or {})) > 0
    if (streak >= 3 and repeat) or streak >= 5:
        R.counter(sid, "fail_streak:" + tool, reset=True)   # one stop, then let her decide
        block("loop_guard", f"`{tool}` has failed {streak} times in a row. Stop retrying the same thing: "
              "tell the person plainly what failed and what you'd suggest (or ask Tiago). "
              "Trying a genuinely different approach is fine.", reason="streak", streak=streak)


FIT_Q = "Is this tool call a sensible step towards doing what the person asked?"
READ_ONLY = {"read_file", "search_files", "skill_view", "skills_list", "session_search", "web_search", "web_extract"}


def check_fit(sid: str, tool: str, args: dict):
    mode_ = R.mode("tool_fit")
    if mode_ == "off" or not sid or tool in READ_ONLY:
        return
    try:
        turn = json.loads((R.STATE_DIR / f"turn-{R._box(sid).stem[6:]}.json").read_text())
    except Exception:
        return
    if time.time() - turn.get("ts", 0) > 1800 or not turn.get("msg"):
        return
    n = R.counter(sid, "fit_sample", 1)
    if mode_ == "shadow" and n % 3 != 1:      # shadow: sample every third call to keep latency low
        return
    state = f"The person asked: {turn['msg'][:900]}\n\nAura is about to call the tool `{tool}` with: " + \
        json.dumps(args, ensure_ascii=False)[:700]
    t = time.time()
    p_fit = R.yes_prob(state, FIT_Q, timeout=3)
    R.log("tool_fit", tool=tool, p_fit=None if p_fit is None else round(p_fit, 3), ms=int((time.time() - t) * 1000))
    if mode_ == "active" and p_fit is not None and p_fit < 0.1:
        key = hashlib.sha256((tool + json.dumps(args, sort_keys=True)).encode()).hexdigest()
        if not speed_bump(key):
            block("tool_fit", "Paused: this tool call doesn't look connected to what the person asked. If it "
                  "is, make the identical call again; otherwise get back to their request.", reason="low_fit")


def main():
    p = R.read_payload()
    if p.get("hook_event_name") not in (None, "pre_tool_call"):
        out()
    tool = p.get("tool_name") or ""
    args = p.get("tool_input") or {}
    if not isinstance(args, dict):
        out()
    if R.who(p.get("session_id") or "") == "metsatron":
        vault_block(tool, args)
    check_loop(p.get("session_id") or "", tool, args)
    try:
        check_fit(p.get("session_id") or "", tool, args)
    except SystemExit:
        raise
    except Exception:
        pass
    if tool == "memory":
        check_memory(args)
    elif tool in pathfix.PATH_ARGS:
        check_paths(p.get("session_id") or "", tool, args, None)   # payload cwd is the gateway's: skip relative paths
    else:
        fixed_cmd = fix_terminal_paths(args.get("command") or "") if tool == "terminal" else None
        if fixed_cmd:
            args = dict(args, command=fixed_cmd)
        lit_fix = check_literal_paths(p.get("session_id") or "", tool, args)   # may block
        if lit_fix:
            args = dict(args, **lit_fix)
        check_risky(tool, args)
        check_missing_commands(tool, args)
        check_writes(tool, args, p.get("cwd"))
        changed = dict(lit_fix or {})
        if fixed_cmd:
            changed.setdefault("command", fixed_cmd)
        if changed:
            out({"action": "modify", "args": changed})
    out()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        print("{}")
        sys.exit(0)
