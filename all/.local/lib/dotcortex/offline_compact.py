#!/usr/bin/env python3
"""Deterministic, provider-free compaction of a Claude session transcript copy.

This is the engine behind ``CLAUDE_IDLE_COMPACT_MODE=deterministic`` in
claude-warm.  It never calls a provider, never injects ``/compact`` and never
touches a live transcript: it reads a COPY, writes a new file, and archives plus
indexes every byte it elides BEFORE that byte leaves the context.

Policy:

  * the last ``keep_recent_records`` records are untouched, whatever their size;
  * elsewhere, a ``tool_result`` block whose text exceeds ``stub_over_chars`` may
    be replaced by a POINTER, never silently deleted (ruling R-0032): the
    replacement names the source transcript path, the 1-based JSONL line of that
    record and the original character count, so the agent can always walk back
    to the full text.  The source transcript is never deleted, so a pointer
    always resolves;
  * user and assistant text is never modified, only tool output;
  * uuid, parentUuid, timestamps, types and record order are never touched.

``STUB_TEMPLATE`` still holds the legacy bare stub of
FORGE/scripts/context_retention/compact_offline.py because that standalone tool
emits it and test-offline-compact-mode.py pins text-extraction parity against
it; this engine writes ``POINTER_TEMPLATE``.

Four rules the standalone tool's CLI cannot express, and that this path exists
to enforce:

  1. **Index before elision.**  Every elided block gets a durable FTS5 row (plus
     a sha256 line in ``elided-index.jsonl``) COMMITTED before the record is
     rewritten.  If the index write fails the pass aborts and the partial output
     is removed: nothing leaves the context without a searchable copy.
  2. **A hard post-compaction ceiling** (default 70_000 tokens).  The keep-set
     is ordered by a relevance selector when one answers, otherwise by recency
     (the deterministic fallback).  If the keep-set is still over the ceiling,
     the lowest-relevance candidates are elided until it is under -- or the pass
     refuses to ship at all.  A session over the ceiling is never installed.
  3. **A labelled selector.**  A Decider ranker (Honey first, Kikin second) may
     order the keep-set; its absence or failure is recorded as ``fallback`` in
     the report and in the supervisor's log.  A selector can only reorder
     elision; it cannot authorise dropping unindexed content or breaching the
     ceiling, and it never touches human text.

Token accounting is explicit: ``chars / chars_per_token`` over message text,
with the assumption printed in the report.  No provider tokenizer is invoked.

  4. **The ceiling is a COLD-RELOAD total, not a transcript budget.**  A resume
     re-reads the harness -- one global instruction file, exactly ONE scope file
     (CLAUDE.md for Claude, AGENTS.md for Codex-style agents; HelmCortex OR
     DotCortex, never both), plus the skill/tool/MCP index estimate -- before it
     reads a single conversation token.  So the conversation is allowed only
     ``ceiling - harness_tokens``.  The harness is measured by
     ``resolve_harness`` / ``measure_harness`` (never a hardcoded 40K), the
     report prints the files it counted so the arithmetic is auditable, and an
     output whose harness + conversation total exceeds the ceiling is refused.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

STUB_TEMPLATE = "[tool output elided: {chars} chars, archived as {key}; first line: {first}]"
POINTER_TEMPLATE = (
    "[elided {chars:,} chars at line {line:,} of {name} \u2014 full text retained; "
    "read it or query the FTS index]"
)

DEFAULT_CEILING_TOKENS = 70_000
DEFAULT_CHARS_PER_TOKEN = 4.0
DEFAULT_KEEP_RECENT_RECORDS = 60
DEFAULT_STUB_OVER_CHARS = 400
DEFAULT_DECIDER_BUDGET_MS = 2_500
DEFAULT_DECIDER_MAX_QUESTIONS = 24
DEFAULT_DECIDER_EXCERPT_CHARS = 600

# Harness accounting (rule 4).  The four combinations below are the only ones a
# seat loads: one global instruction file plus exactly ONE scope file, chosen by
# agent family and scope.  Hermes carries its own harness and is excluded rather
# than modelled as a normal seat.
HARNESS_FAMILY_FILENAME = {"claude": "CLAUDE.md", "codex": "AGENTS.md"}
HARNESS_SCOPE_DIRECTORY = {"helmcortex": "HelmCortex", "dotcortex": "DotCortex"}
HARNESS_EXCLUDED_FAMILIES = frozenset({"hermes"})
HARNESS_SCHEMA = "dotcortex.harness-baseline.v1"
# Documented fallback ONLY when measurement is impossible (no global file, no
# scope file, or an unreadable one).  The measured pairs on this machine are
# ~10.6k (Claude/DotCortex) to ~16.4k (Codex/HelmCortex) tokens; 20k therefore
# over-reserves, which is the safe direction for a ceiling.
DEFAULT_HARNESS_ESTIMATE_TOKENS = 20_000

# The deployed approval gate ships placeholder URLs until a host is wired
# (all/.config/dotcortex/claude-approval-*.json); the same law applies here --
# never commit a real address, and treat a placeholder as "no endpoint".
KIKIN_PLACEHOLDER_URL = "http://YOUR_DECIDER_HOST/v1/systemone"

DECIDER_KEEP_QUESTION = (
    "Is this transcript item worth keeping verbatim in the agent's working "
    "context: does it carry facts, decisions or file state the agent still "
    "needs to continue its current work?"
)

UUID4_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)


class ChainError(RuntimeError):
    """The parent chain of a transcript is broken (a resume would truncate)."""


@dataclass
class Candidate:
    """One elidable tool_result block (what the ceiling is allowed to drop)."""

    key: str
    position: int
    block_index: int
    chars: int
    uuid: str | None
    excerpt: str


@dataclass
class RankOutcome:
    """What a relevance selector produced, and how it failed if it did."""

    scores: dict[str, float] = field(default_factory=dict)
    selector: str = "fallback:no-selector"
    status: str = "unavailable"
    endpoint: str | None = None
    latency_ms: int = 0
    answered: int = 0

    @property
    def usable(self) -> bool:
        return bool(self.scores)


@dataclass
class CompactResult:
    ok: bool
    reason: str | None
    report: dict
    out_path: Path | None = None
    index_path: Path | None = None


# --------------------------------------------------------------------------
# text extraction -- same rules as compact_offline.py
# --------------------------------------------------------------------------


PROSE_BLOCK_TYPES = ("text", "tool_use")


def block_text(part: dict) -> str:
    """The text a block carries, whatever kind of block it is.

    Tool output lives in ``content``; prose lives in ``text``; a tool call's
    arguments live in ``input``.  Folding an old prose turn or an old tool call
    needs all three, so the extractor speaks for all three instead of pretending
    every block is a tool result.
    """
    kind = part.get("type")
    if kind == "tool_result":
        return text_of_part(part)
    if kind == "text":
        value = part.get("text")
        return value if isinstance(value, str) else ""
    if kind == "tool_use":
        return json.dumps(part.get("input") or {}, ensure_ascii=False, sort_keys=True)
    return ""


def staged_stub(part: dict, stub: str) -> dict:
    """The block with its text replaced by a pointer, in the field that held it.

    A tool_result keeps its ``content`` key, a text block keeps ``text``, and a
    tool call keeps a structurally valid ``input`` whose only member is the
    pointer -- so the record still parses as a tool call while carrying no prose.
    """
    kind = part.get("type")
    out = {key: value for key, value in part.items()}
    if kind == "tool_use":
        out["input"] = {"_elided_pointer": stub}
        return out
    if kind == "text":
        out["text"] = stub
        return out
    out.pop("content", None)
    out["content"] = stub
    return out


def text_of_part(part: dict) -> str:
    content = part.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(x.get("text", "") for x in content if isinstance(x, dict))
    return ""


CONTEXT_RECORD_TYPES = ("user", "assistant")


def is_context_record(record: dict) -> bool:
    """True when the model reads this record on resume.

    A transcript also carries records a logging mod wrote beside the
    conversation (api-request-blob, api-request, api-request-shape, ...). They
    have a ``message`` field, but they are not conversation: counting them fills
    the ceiling with text the model never loads, and an index stub placed in one
    of them is a pointer the model cannot read. A record with no type is treated
    as conversation, so older fixtures keep working.
    """
    kind = record.get("type")
    return kind is None or kind in CONTEXT_RECORD_TYPES


def all_text(record: dict) -> int:
    """Every character of message text in this record, tool output included.

    Zero for a record the model does not read (see is_context_record)."""
    if not is_context_record(record):
        return 0
    message = record.get("message")
    if not isinstance(message, dict):
        return 0
    content = message.get("content")
    if isinstance(content, str):
        return len(content)
    total = 0
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use":
                # A tool call's arguments are prose the model reads back too.
                total += len(block_text(part))
            elif isinstance(part.get("text"), str):
                total += len(part["text"])
            else:
                total += len(text_of_part(part))
    return total


def human_text(record: dict) -> str:
    """Only the words a human or the assistant typed: tool output excluded."""
    message = record.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    chunks = []
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") != "tool_result":
                if isinstance(part.get("text"), str):
                    chunks.append(part["text"])
    return "\n".join(chunks)


def estimate_tokens(chars: int, chars_per_token: float = DEFAULT_CHARS_PER_TOKEN) -> int:
    if chars_per_token <= 0:
        chars_per_token = DEFAULT_CHARS_PER_TOKEN
    return int(round(chars / chars_per_token))


def tokenizer_label(chars_per_token: float) -> str:
    return "chars/{:g}".format(chars_per_token)


# --------------------------------------------------------------------------
# transcript IO and chain integrity
# --------------------------------------------------------------------------


def load_records_with_lines(path: Path) -> list[tuple[int, dict]]:
    """Read a JSONL transcript as (1-based line number, record) pairs.

    The line number is the PHYSICAL line in the file, because that is what a
    pointer stub promises the agent.  Blank lines are skipped but never
    renumbered: a pointer to line 3,412 must name line 3,412 of the file on
    disk, so the numbering can never drift from what ``readline`` reports.
    """
    rows: list[tuple[int, dict]] = []
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, start=1):
            if line.strip():
                rows.append((number, json.loads(line)))
    return rows


def load_records(path: Path) -> list[dict]:
    return [record for _number, record in load_records_with_lines(path)]


def parent_chain(records: list[dict]) -> list[str]:
    """Walk parentUuid from the newest uuid-bearing record to the root.

    Returns uuids newest-first.  Raises ChainError when a parent is missing or
    the graph cycles: a compacted copy that cannot reproduce the chain would
    resume with a truncated history, so the caller must refuse.
    """
    by_uuid: dict[str, dict] = {}
    for record in records:
        value = record.get("uuid")
        if isinstance(value, str) and value:
            by_uuid[value] = record
    tail = None
    for record in reversed(records):
        value = record.get("uuid")
        if isinstance(value, str) and value:
            tail = value
            break
    if tail is None:
        return []
    chain = [tail]
    seen = {tail}
    node = by_uuid[tail]
    while True:
        parent = node.get("parentUuid")
        if parent in (None, ""):
            return chain
        if not isinstance(parent, str):
            raise ChainError("non-string parentUuid {!r} on {!r}".format(parent, node.get("uuid")))
        if parent not in by_uuid:
            raise ChainError("missing parent {!r} referenced by {!r}".format(parent, node.get("uuid")))
        if parent in seen:
            raise ChainError("parent cycle at {!r}".format(parent))
        seen.add(parent)
        chain.append(parent)
        node = by_uuid[parent]


def main_chain(records: list[dict]) -> tuple[list[str], list[dict]]:
    """The real chain, tolerating a trailing orphan fragment.

    Walk back from the newest uuid-bearing record exactly as parent_chain does.
    When that record's chain does not reach the root (a missing parent, a
    cycle), it is a trailing orphan: report it and try the next-newest, until
    one reaches the root. The chain is never shortened and nothing is dropped
    silently: every skipped record is returned with its position, role, uuid and
    the reason. When no record reaches the root, ChainError is raised as before.

    Returns (chain newest-first, orphans oldest-first).
    """
    positions = [
        position
        for position, record in enumerate(records)
        if isinstance(record.get("uuid"), str) and record.get("uuid")
    ]
    orphans: list[dict] = []
    for position in reversed(positions):
        try:
            chain = parent_chain(records[: position + 1])
        except ChainError as error:
            record = records[position]
            orphans.append(
                {
                    "position": position,
                    "type": record.get("type"),
                    "role": (record.get("message") or {}).get("role") if isinstance(record.get("message"), dict) else None,
                    "uuid": record.get("uuid"),
                    "parentUuid": record.get("parentUuid"),
                    "reason": str(error),
                    "excluded": True,
                }
            )
            continue
        orphans.reverse()
        return chain, orphans
    if not positions:
        return [], []
    raise ChainError(
        "no uuid-bearing record reaches the root; newest failure: {}".format(
            orphans[0]["reason"] if orphans else "unknown"
        )
    )


def repair_orphan_chain(lines: list[str]) -> tuple[list[str], list[dict]]:
    """Reconnect a trailing orphan fragment to the real tip by rewriting ONE parentUuid.

    Native Claude Code's failed /compact (a 5-hour-limited one, 17 Nov 2026) writes a
    record whose parentUuid names a uuid that no record defines. ``claude --resume``
    walks back from the newest record, stops at that dangling parent and loads only the
    fragment, dropping everything older. The repair sets the fragment's first record's
    parentUuid to the newest record that does reach the root (the real tip) and touches
    no other byte of the transcript.

    Takes raw lines (newlines kept) and returns (new lines, repairs). Returns the lines
    unchanged and an empty list when there is no orphan. Raises ChainError, changing
    nothing, when the damage is not exactly one fragment hanging off one missing uuid:
    a cycle, a second gap, a fragment whose members do not chain to its first record, or
    a line whose parentUuid cannot be rewritten with the result parsing to exactly the
    expected record.
    """
    live = [(index, line) for index, line in enumerate(lines) if line.strip()]
    records = [json.loads(line) for _index, line in live]
    chain, orphans = main_chain(records)
    if not orphans:
        return list(lines), []
    first = orphans[0]
    missing = first["parentUuid"]
    defined = {r.get("uuid") for r in records if isinstance(r.get("uuid"), str)}
    if not isinstance(missing, str) or not missing or missing in defined:
        raise ChainError("the first orphan is not hanging off a missing parent: {}".format(first["reason"]))
    fragment = {first["uuid"]}
    for orphan in orphans[1:]:
        if orphan["parentUuid"] not in fragment:
            raise ChainError(
                "orphan {!r} does not chain to the fragment's first record; more than one gap".format(orphan["uuid"])
            )
        fragment.add(orphan["uuid"])
    tip = chain[0]
    line_index = live[first["position"]][0]
    old = lines[line_index]
    needle = '"parentUuid":"{}"'.format(missing)
    if old.count(needle) < 1:
        raise ChainError("line {} does not carry {} in the compact form".format(line_index + 1, needle))
    new = old.replace(needle, '"parentUuid":"{}"'.format(tip), 1)
    expected = dict(records[first["position"]])
    expected["parentUuid"] = tip
    if json.loads(new) != expected:
        raise ChainError("line {}: the rewrite changed more than parentUuid; refusing".format(line_index + 1))
    repaired = list(lines)
    repaired[line_index] = new
    after_chain, after_orphans = main_chain([json.loads(line) for line in repaired if line.strip()])
    if after_orphans:
        raise ChainError("the repair did not reconnect the fragment; refusing")
    return repaired, [
        {
            "line": line_index + 1,
            "uuid": first["uuid"],
            "old_parentUuid": missing,
            "new_parentUuid": tip,
            "fragment_records": len(orphans),
            "chain_records": len(after_chain),
        }
    ]


def repair_orphan_chain_file(source: Path, out: Path) -> list[dict]:
    """Write a repaired copy of a transcript to ``out``; never edits ``source``.

    Returns the repairs made. Writes nothing when the chain is already whole. ``out``
    must be a different path from ``source``: swapping the repaired copy into place is
    the caller's act, done only while the seat that owns the session is stopped.
    """
    source, out = Path(source), Path(out)
    if out.resolve() == source.resolve():
        raise ChainError("refusing to repair in place: pass a different output path")
    with source.open("r", encoding="utf-8", newline="") as handle:
        lines = handle.readlines()
    repaired, report = repair_orphan_chain(lines)
    if not report:
        return []
    partial = out.with_name(out.name + ".partial")
    with partial.open("w", encoding="utf-8", newline="") as handle:
        handle.writelines(repaired)
    partial.replace(out)
    return report


SUMMARY_PREFIX = "This session is being continued from a previous conversation"


def newest_summary_position(records: list[dict], excluded: set[int] | None = None) -> int | None:
    """Position of the newest whole-string user record that is a carried summary."""
    skip = excluded or set()
    for position in range(len(records) - 1, -1, -1):
        if position in skip:
            continue
        record = records[position]
        if not is_context_record(record):
            continue
        message = record.get("message")
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) and content.startswith(SUMMARY_PREFIX):
            return position
    return None


def identity_snapshot(records: list[dict]) -> list[tuple]:
    """The fields that must survive compaction byte-for-byte."""
    return [
        (record.get("uuid"), record.get("parentUuid"), record.get("timestamp"), record.get("type"))
        for record in records
    ]


# --------------------------------------------------------------------------
# index + archive
# --------------------------------------------------------------------------

INDEX_SCHEMA = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS elided USING fts5("
    "key UNINDEXED, sha256 UNINDEXED, chars UNINDEXED, body)"
)

# A pointer may point at an INDEX OF POINTERS rather than at one block.  The
# group row is the summary the operator asked for: a collection of elided
# blocks described by task and project, so the stub itself says what it covers
# instead of being a bare "something was here".  Members are listed separately
# so a group stub can be expanded back into the individual pointers.
GROUP_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS pointer_groups("
    "gid TEXT PRIMARY KEY, label TEXT, project TEXT, summary TEXT, "
    "chars INTEGER, blocks INTEGER, first_line INTEGER, last_line INTEGER)"
)
# The line of the source transcript each archived block came from.  A pointer
# names that line, so the reader has to find a block BY LINE; the record position
# in a key is not the line when the source has blank or skipped lines.
LINE_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS elided_lines("
    "key TEXT PRIMARY KEY, line INTEGER)"
)
MEMBER_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS pointer_group_members("
    "gid TEXT, key TEXT, line INTEGER, uuid TEXT, chars INTEGER, "
    "PRIMARY KEY (gid, key))"
)



class ElisionIndex:
    """Durable archive + FTS5 index of every elided block.

    ``add`` is the only mutation and it is synchronous (``PRAGMA
    synchronous=FULL``), so the caller may rewrite the record only after ``add``
    returns.  That ordering is the "nothing is dropped unless its index entry
    exists first" rule, and it is what test-offline-compact-mode.py asserts.
    """

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.index_path = self.directory / "elided-index.jsonl"
        self.database_path = self.directory / "elided.sqlite3"
        self.connection = sqlite3.connect(str(self.database_path))
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(INDEX_SCHEMA)
        self.connection.execute(GROUP_SCHEMA)
        self.connection.execute(MEMBER_SCHEMA)
        self.connection.execute(LINE_SCHEMA)
        self.connection.commit()
        fd = os.open(self.index_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        self.journal = os.fdopen(fd, "a", encoding="utf-8")
        self.count = 0

    def add(self, key: str, body: str, line: int | None = None) -> str:
        """Archive and index one block; returns its sha256."""
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.journal.write(json.dumps({"key": key, "sha256": digest, "chars": len(body)}) + "\n")
        self.journal.flush()
        os.fsync(self.journal.fileno())
        self.connection.execute(
            "INSERT INTO elided(key, sha256, chars, body) VALUES (?, ?, ?, ?)",
            (key, digest, len(body), body),
        )
        if line is not None:
            self.connection.execute(
                "INSERT OR REPLACE INTO elided_lines(key, line) VALUES (?, ?)", (key, int(line))
            )
        self.connection.commit()
        self.count += 1
        return digest

    def search(self, query: str, limit: int = 10) -> list[str]:
        rows = self.connection.execute(
            "SELECT key FROM elided WHERE elided MATCH ? LIMIT ?", (query, limit)
        ).fetchall()
        return [row[0] for row in rows]

    def add_group(self, group: dict) -> None:
        """Record one pointer group and its members, committed before use.

        The group row carries the summary; the member rows carry the individual
        pointers it stands for.  A group stub whose ``gid`` is not here, or whose
        member count disagrees, is refused by ``verify_groups`` -- a group stub is
        a promise that the index it names can expand it.
        """
        self.connection.execute(
            "INSERT OR REPLACE INTO pointer_groups"
            "(gid, label, project, summary, chars, blocks, first_line, last_line)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                group["gid"],
                group.get("label", ""),
                group.get("project", ""),
                group.get("summary", ""),
                int(group.get("chars") or 0),
                int(group.get("blocks") or len(group.get("members") or [])),
                int(group.get("first_line") or 0),
                int(group.get("last_line") or 0),
            ),
        )
        for member in group.get("members") or []:
            self.connection.execute(
                "INSERT OR REPLACE INTO pointer_group_members"
                "(gid, key, line, uuid, chars) VALUES (?, ?, ?, ?, ?)",
                (
                    group["gid"],
                    member["key"],
                    int(member.get("line") or 0),
                    member.get("uuid"),
                    int(member.get("chars") or 0),
                ),
            )
        self.connection.commit()

    def group_members(self, gid: str) -> list[dict]:
        rows = self.connection.execute(
            "SELECT key, line, uuid, chars FROM pointer_group_members"
            " WHERE gid = ? ORDER BY line",
            (gid,),
        ).fetchall()
        return [
            {"key": row[0], "line": row[1], "uuid": row[2], "chars": row[3]} for row in rows
        ]

    def body(self, key: str) -> str | None:
        row = self.connection.execute("SELECT body FROM elided WHERE key = ?", (key,)).fetchone()
        return None if row is None else row[0]

    def has_group(self, gid: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM pointer_groups WHERE gid = ?", (gid,)
        ).fetchone()
        return row is not None

    def close(self) -> None:
        try:
            self.connection.close()
        finally:
            try:
                self.journal.close()
            except OSError:
                pass


# --------------------------------------------------------------------------
# harness accounting: what a cold reload pays before the conversation
# --------------------------------------------------------------------------


class HarnessScopeError(ValueError):
    """The harness resolver was given an ambiguous scope (two files, or none)."""


@dataclass
class HarnessBaseline:
    """What one cold reload pays before it reads a single conversation token."""

    family: str
    scope: str
    tokens: int
    chars: int
    index_tokens: int = 0
    source: str = "measured"
    files: list = field(default_factory=list)

    def as_report(self) -> dict:
        return {
            "harness_family": self.family,
            "harness_scope": self.scope,
            "harness_tokens": int(self.tokens),
            "harness_chars": int(self.chars),
            "harness_index_tokens": int(self.index_tokens),
            "harness_source": self.source,
            "harness_files": [dict(item) for item in self.files],
        }


def _normalised(value: object) -> str:
    return str(value or "").strip().lower()


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


def _harness_estimate(
    family: str,
    scope: str,
    index_tokens: int,
    reason: str,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
) -> HarnessBaseline:
    """The documented fallback, labelled with WHY it had to be used."""
    return HarnessBaseline(
        family=family,
        scope=scope,
        tokens=DEFAULT_HARNESS_ESTIMATE_TOKENS + int(index_tokens),
        chars=int(DEFAULT_HARNESS_ESTIMATE_TOKENS * float(chars_per_token)),
        index_tokens=int(index_tokens),
        source=reason,
        files=[],
    )


def _harness_paths(
    family: str,
    scope: str,
    home: Path | None = None,
    scope_files: list[Path] | None = None,
) -> tuple[Path | None, Path] | None:
    """Name the two files a seat loads, or None when the pair is unnameable."""
    family, scope = _normalised(family), _normalised(scope)
    if family not in HARNESS_FAMILY_FILENAME or scope not in HARNESS_SCOPE_DIRECTORY:
        return None
    home = Path(home).expanduser() if home is not None else Path.home()
    filename = HARNESS_FAMILY_FILENAME[family]
    if scope_files is not None:
        supplied = [Path(item).expanduser() for item in scope_files]
        if len(supplied) != 1:
            raise HarnessScopeError(
                "harness-scope-ambiguous: {} scope files supplied ({}); a seat "
                "loads exactly one".format(
                    len(supplied), ", ".join(str(item) for item in supplied) or "none"
                )
            )
        scope_path = supplied[0]
    else:
        scope_path = home / HARNESS_SCOPE_DIRECTORY[scope] / filename
    global_path = _first_existing(
        [home / ".claude" / filename, home / filename, home / ".claude" / "CLAUDE.md"]
    )
    return global_path, scope_path


def resolve_harness(
    family: str,
    scope: str,
    *,
    home: Path | None = None,
    scope_files: list[Path] | None = None,
    index_tokens: int = 0,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
) -> HarnessBaseline:
    """Measure ONE global instruction file plus exactly ONE scope file.

    ``family`` is the agent family (``claude`` reads CLAUDE.md, Codex-style
    agents read AGENTS.md); ``scope`` is ``helmcortex`` or ``dotcortex``.  The
    two names are never summed, and the two scopes are never summed: doing
    either doubles the harness and starves the conversation.  A caller that
    supplies two scope files is refused loudly instead of quietly counting both.
    Hermes is excluded -- it carries its own harness and is not a normal seat --
    so its baseline is zero and the report says ``excluded:hermes``.
    """
    family, scope = _normalised(family), _normalised(scope)
    index_tokens = max(0, int(index_tokens))
    if family in HARNESS_EXCLUDED_FAMILIES:
        return HarnessBaseline(family, scope, 0, 0, index_tokens, "excluded:hermes", [])
    paths = _harness_paths(family, scope, home, scope_files)
    if paths is None:
        reason = (
            "estimate:family-unknown"
            if family not in HARNESS_FAMILY_FILENAME
            else "estimate:scope-unknown"
        )
        return _harness_estimate(family, scope, index_tokens, reason, chars_per_token)
    global_path, scope_path = paths
    if global_path is None or not scope_path.is_file():
        return _harness_estimate(
            family, scope, index_tokens, "estimate:measurement-failed", chars_per_token
        )
    files: list[dict] = []
    chars = 0
    for role, path in (("global", global_path), ("scope", scope_path)):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return _harness_estimate(
                family, scope, index_tokens, "estimate:measurement-failed", chars_per_token
            )
        files.append({"role": role, "path": str(path), "chars": len(text)})
        chars += len(text)
    return HarnessBaseline(
        family=family,
        scope=scope,
        tokens=estimate_tokens(chars, chars_per_token) + index_tokens,
        chars=chars,
        index_tokens=index_tokens,
        source="measured",
        files=files,
    )


def harness_signature(
    paths: list[Path], family: str, scope: str, index_tokens: int = 0
) -> str:
    """Cheap identity of the counted files: a cache hit then needs no read."""
    material = [_normalised(family), _normalised(scope), str(int(index_tokens))]
    for path in paths:
        try:
            stat = path.stat()
            material.append("{}:{}:{}".format(path, stat.st_size, stat.st_mtime_ns))
        except OSError:
            material.append("{}:missing".format(path))
    return hashlib.sha256("\n".join(material).encode("utf-8")).hexdigest()


def _read_harness_cache(cache_path: Path, seat: str | None, signature: str) -> HarnessBaseline | None:
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != HARNESS_SCHEMA:
        return None
    if payload.get("signature") != signature or payload.get("seat") != seat:
        return None
    report = payload.get("baseline")
    if not isinstance(report, dict):
        return None
    tokens = report.get("harness_tokens")
    if isinstance(tokens, bool) or not isinstance(tokens, int):
        return None
    files = report.get("harness_files")
    return HarnessBaseline(
        family=str(report.get("harness_family") or ""),
        scope=str(report.get("harness_scope") or ""),
        tokens=tokens,
        chars=int(report.get("harness_chars") or 0),
        index_tokens=int(report.get("harness_index_tokens") or 0),
        source="cache",
        files=[item for item in files if isinstance(item, dict)] if isinstance(files, list) else [],
    )


def _write_harness_cache(
    cache_path: Path, seat: str | None, signature: str, baseline: HarnessBaseline
) -> None:
    payload = {
        "schema": HARNESS_SCHEMA,
        "seat": seat,
        "signature": signature,
        "measured_at": int(time.time()),
        "baseline": baseline.as_report(),
    }
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_name(cache_path.name + ".tmp")
        temporary.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        os.replace(temporary, cache_path)
    except OSError:
        # A cache that cannot be written is a slow path, never a failed pass.
        pass


def measure_harness(
    family: str,
    scope: str,
    *,
    home: Path | None = None,
    scope_files: list[Path] | None = None,
    index_tokens: int = 0,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
    cache_path: Path | None = None,
    seat: str | None = None,
    override_tokens: int = 0,
    refresh: bool = False,
) -> HarnessBaseline:
    """Measure the harness once, cache it per seat, and label where it came from.

    ``override_tokens`` (CLAUDE_IDLE_COMPACT_HARNESS_TOKENS) wins outright and is
    reported as ``override``.  The cache is keyed by seat AND by the (path, size,
    mtime) signature of the two counted files, so a changed instruction file
    re-measures and an unchanged one costs two stats.  Everything that cannot be
    measured falls back to the documented estimate with the reason in ``source``.
    """
    family, scope = _normalised(family), _normalised(scope)
    if int(override_tokens or 0) > 0:
        return HarnessBaseline(
            family=family,
            scope=scope,
            tokens=int(override_tokens),
            chars=int(int(override_tokens) * float(chars_per_token)),
            index_tokens=0,
            source="override",
            files=[],
        )
    index_tokens = max(0, int(index_tokens))
    paths = _harness_paths(family, scope, home, scope_files)
    signature = None
    if paths is not None:
        signature = harness_signature(
            [path for path in paths if path is not None], family, scope, index_tokens
        )
    if cache_path is not None and signature is not None and not refresh:
        cached = _read_harness_cache(Path(cache_path), seat, signature)
        if cached is not None:
            return cached
    baseline = resolve_harness(
        family,
        scope,
        home=home,
        scope_files=scope_files,
        index_tokens=index_tokens,
        chars_per_token=chars_per_token,
    )
    if cache_path is not None and signature is not None and baseline.source == "measured":
        _write_harness_cache(Path(cache_path), seat, signature, baseline)
    return baseline


# --------------------------------------------------------------------------
# relevance selection (Decider: Honey first, Kikin second)
# --------------------------------------------------------------------------


def _live_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value.startswith(("http://", "https://")):
        return None
    if "YOUR_" in value:
        return None
    return value


def _post_json(url: str, payload: dict, timeout_ms: int) -> tuple[dict | None, str]:
    """One bounded POST.  Returns (decoded, status); never raises."""
    import socket
    import urllib.error
    import urllib.request

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DotCortex-claude-warm/offline-compact",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(0.05, timeout_ms / 1000.0)) as response:
            raw = response.read(8 * 1024 * 1024)
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            return None, "invalid"
        return decoded, "ok"
    except (socket.timeout, TimeoutError):
        # socket.timeout is an OSError subclass: name it first so a slow
        # endpoint is never mislabelled as unavailable.
        return None, "timeout"
    except (urllib.error.HTTPError, urllib.error.URLError, ConnectionError, OSError):
        return None, "unavailable"
    except (TypeError, ValueError):
        return None, "invalid"


def _r2d2d_scores(decoded: dict, ids: list[str]) -> dict[str, float] | None:
    answers = decoded.get("answers")
    if not isinstance(answers, list) or len(answers) != len(ids):
        return None
    scores: dict[str, float] = {}
    for key, answer in zip(ids, answers):
        p_yes = answer.get("p_yes") if isinstance(answer, dict) else None
        if isinstance(p_yes, bool) or not isinstance(p_yes, (int, float)):
            return None
        p_yes = float(p_yes)
        if not math.isfinite(p_yes) or p_yes < 0.0 or p_yes > 1.0:
            return None
        scores[key] = p_yes
    return scores


def _kikin_scores(decoded: dict, ids: list[str]) -> dict[str, float] | None:
    answers = decoded.get("answers")
    if not isinstance(answers, dict):
        return None
    scores: dict[str, float] = {}
    for index, key in enumerate(ids):
        answer = answers.get("q{}".format(index))
        value = answer.get("noul") if isinstance(answer, dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        value = float(value)
        if not math.isfinite(value) or value < 0.0 or value > 1.0:
            return None
        scores[key] = value
    return scores


class DeciderRanker:
    """Ask the System One Decider which elidable items to keep verbatim.

    Honey (r2d2d ``/decide``) is asked first; Kikin (``/v1/systemone``) second,
    each with the REMAINING budget (never the full budget twice).  One question
    per candidate rides a single request per endpoint.  Every failure mode is
    "no ranking": the deterministic recency fallback then runs and the report
    says so.
    """

    def __init__(
        self,
        honey_url: str | None = None,
        kikin_url: str | None = None,
        budget_ms: int = DEFAULT_DECIDER_BUDGET_MS,
        max_questions: int = DEFAULT_DECIDER_MAX_QUESTIONS,
        excerpt_chars: int = DEFAULT_DECIDER_EXCERPT_CHARS,
    ):
        self.honey_url = _live_url(honey_url)
        self.kikin_url = _live_url(kikin_url)
        self.budget_ms = max(200, int(budget_ms))
        self.max_questions = max(1, int(max_questions))
        self.excerpt_chars = max(80, int(excerpt_chars))

    @classmethod
    def from_env(cls, env: dict | None = None) -> "DeciderRanker | None":
        values: dict = dict(os.environ) if env is None else dict(env)
        if str(values.get("CLAUDE_IDLE_COMPACT_DECIDER", "auto")).strip().lower() == "off":
            return None
        honey = values.get("CLAUDE_IDLE_COMPACT_HONEY_DECIDER_URL") or values.get(
            "SO_APPROVAL_HONEY_DECIDER_URL"
        )
        kikin = (
            values.get("CLAUDE_IDLE_COMPACT_KIKIN_DECIDER_URL")
            or values.get("SO_APPROVAL_KIKIN_DECIDER_URL")
            or KIKIN_PLACEHOLDER_URL
        )
        try:
            budget_ms = int(
                values.get("CLAUDE_IDLE_COMPACT_DECIDER_BUDGET_MS", DEFAULT_DECIDER_BUDGET_MS)
            )
        except (TypeError, ValueError):
            budget_ms = DEFAULT_DECIDER_BUDGET_MS
        try:
            max_questions = int(
                values.get("CLAUDE_IDLE_COMPACT_DECIDER_MAX_QUESTIONS", DEFAULT_DECIDER_MAX_QUESTIONS)
            )
        except (TypeError, ValueError):
            max_questions = DEFAULT_DECIDER_MAX_QUESTIONS
        ranker = cls(honey, kikin, budget_ms=budget_ms, max_questions=max_questions)
        if not ranker.honey_url and not ranker.kikin_url:
            return None
        return ranker

    def rank(self, candidates: list[Candidate]) -> RankOutcome:
        import time as _time

        outcome = RankOutcome()
        if not candidates:
            outcome.selector = "fallback:no-candidates"
            outcome.status = "empty"
            return outcome
        # Ask about the largest blocks: they are what the ceiling depends on.
        ordered = sorted(candidates, key=lambda c: (-c.chars, c.position))[: self.max_questions]
        ids = [c.key for c in ordered]
        by_key = {c.key: c for c in ordered}
        state = {
            "task": "claude-warm offline compaction",
            "items": [
                {"id": key, "chars": by_key[key].chars, "excerpt": by_key[key].excerpt}
                for key in ids
            ],
        }
        questions_text = [
            {"question": "{} (item {})".format(DECIDER_KEEP_QUESTION, key), "type": "noul"}
            for key in ids
        ]
        started = _time.monotonic()
        deadline = started + self.budget_ms / 1000.0

        # Honey first (r2d2d shape: one shared state, questions list, p_yes).
        if self.honey_url:
            remaining = int((deadline - _time.monotonic()) * 1000)
            if remaining >= 200:
                payload = {"state": json.dumps(state), "questions": questions_text}
                decoded, status = _post_json(self.honey_url, payload, remaining)
                outcome.status = status
                outcome.endpoint = "honey"
                if decoded is not None:
                    scores = _r2d2d_scores(decoded, ids)
                    if scores is not None:
                        outcome.scores = scores
                        outcome.selector = "decider:honey"
                        outcome.status = "ok"
                        outcome.answered = len(scores)
                        outcome.latency_ms = int((_time.monotonic() - started) * 1000)
                        return outcome
                    outcome.status = "invalid"
                if outcome.status == "timeout":
                    outcome.latency_ms = int((_time.monotonic() - started) * 1000)
                    outcome.selector = "fallback:decider-timeout"
                    return outcome
            else:
                outcome.status = "timeout"

        # Kikin second, with only what is left of the one shared budget.
        if self.kikin_url:
            remaining = int((deadline - _time.monotonic()) * 1000)
            if remaining >= 200:
                payload = {
                    "questions": {
                        "q{}".format(index): {
                            "type": "noul",
                            "instructions": "Judge one transcript item for compaction.",
                            "criteria": {"keep": DECIDER_KEEP_QUESTION},
                            "evidence_ids": [key],
                        }
                        for index, key in enumerate(ids)
                    },
                    "state": state,
                    "limits": {"deadline_ms": remaining},
                }
                decoded, status = _post_json(self.kikin_url, payload, remaining)
                outcome.status = status
                outcome.endpoint = "kikin"
                if decoded is not None:
                    scores = _kikin_scores(decoded, ids)
                    if scores is not None:
                        outcome.scores = scores
                        outcome.selector = "decider:kikin"
                        outcome.status = "ok"
                        outcome.answered = len(scores)
                        outcome.latency_ms = int((_time.monotonic() - started) * 1000)
                        return outcome
                    outcome.status = "invalid"

        outcome.latency_ms = int((_time.monotonic() - started) * 1000)
        outcome.selector = "fallback:decider-{}".format(outcome.status or "unavailable")
        return outcome


# --------------------------------------------------------------------------
# candidate selection and the ceiling
# --------------------------------------------------------------------------


def elidable_candidates(
    records: list[dict],
    keep_recent_records: int,
    stub_over_chars: int,
    excerpt_chars: int = DEFAULT_DECIDER_EXCERPT_CHARS,
    include_prose: bool = False,
) -> list[Candidate]:
    boundary = max(0, len(records) - max(0, keep_recent_records))
    found: list[Candidate] = []
    for position, record in enumerate(records[:boundary]):
        if not is_context_record(record):
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            # A record whose whole content is one string: Claude Code writes the
            # native compaction summary ("This session is being continued...")
            # and every channel message this way. block_index -1 names it.
            if include_prose and len(content) > stub_over_chars:
                found.append(
                    Candidate(
                        key="r{}-s".format(position),
                        position=position,
                        block_index=-1,
                        chars=len(content),
                        uuid=record.get("uuid") if isinstance(record.get("uuid"), str) else None,
                        excerpt="\n".join(content.splitlines()[:6])[:excerpt_chars],
                    )
                )
            continue
        if not isinstance(content, list):
            continue
        for block_index, part in enumerate(content):
            kinds = ("tool_result",) + (PROSE_BLOCK_TYPES if include_prose else ())
            if not isinstance(part, dict) or part.get("type") not in kinds:
                continue
            text = block_text(part)
            if len(text) <= stub_over_chars:
                continue
            excerpt = "\n".join(text.splitlines()[:6])[:excerpt_chars]
            found.append(
                Candidate(
                    key="r{}-{}".format(position, block_index),
                    position=position,
                    block_index=block_index,
                    chars=len(text),
                    uuid=record.get("uuid") if isinstance(record.get("uuid"), str) else None,
                    excerpt=excerpt,
                )
            )
    return found


def drop_order(candidates: list[Candidate], scores: dict[str, float] | None) -> list[Candidate]:
    """Lowest relevance first; unscored items sit at neutral 0.5.

    Neutral is deliberate: an item the Decider never judged is neither proof of
    relevance nor proof of irrelevance, so it is dropped after genuinely
    low-relevance items and before genuinely high-relevance ones.  Within a
    score band the oldest and largest go first, which is the deterministic
    fallback order when no selector answered at all.
    """
    scores = scores or {}
    return sorted(
        candidates,
        key=lambda c: (scores.get(c.key, 0.5), c.position, -c.chars),
    )


def pointer_text(chars: int, line: int, name: str) -> str:
    """The replacement for an elided block: a POINTER into the full transcript.

    Ruling R-0032: an elided block is not deleted, it is moved out of the working
    context and pointed at.  The pointer names the source file, the 1-based JSONL
    line of that record and the original character count, so the agent can read
    the full text back or query the FTS index for it.  The source transcript is
    never deleted, so every pointer resolves.
    """
    return POINTER_TEMPLATE.format(chars=int(chars), line=int(line), name=name)


POINTER_LINE_RE = re.compile(r"at line ([\d,]+) of ")


def pointer_line(text: object) -> int | None:
    """The line number a pointer stub CLAIMS, or None when it names none.

    Verification reads this number out of the text it actually wrote, never from
    the bookkeeping around it: a pointer whose printed line disagrees with the
    record it came from must be caught, and only the text is what the agent sees.
    """
    match = POINTER_LINE_RE.search(str(text))
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def stub_length_bound(candidate: Candidate, name: str = "source.jsonl", line: int = 10**9) -> int:
    """Upper bound on a pointer's length for this candidate.

    ``line`` defaults to a nine-digit number so the bound never under-counts when
    the real line is shorter than the bound assumes; the ceiling arithmetic below
    therefore always errs toward eliding one more block, never toward breaching
    the ceiling.
    """
    return len(pointer_text(candidate.chars, line, name))


def choose_elisions(
    candidates: list[Candidate],
    chars_before: int,
    ceiling_tokens: int,
    chars_per_token: float,
    scores: dict[str, float] | None,
    *,
    pointer_name: str = "source.jsonl",
    max_line: int = 10**9,
) -> tuple[list[Candidate], int]:
    """Elide lowest-relevance candidates until the ceiling is met.

    Returns (chosen, chars_after).  ``ceiling_tokens`` is the CONVERSATION budget
    (the cold-reload ceiling minus the measured harness), and comparison happens
    in characters -- the unit actually measured -- so rounding never hides a
    breach of the ceiling.
    """
    ceiling_chars = ceiling_tokens * chars_per_token
    remaining = chars_before
    chosen: list[Candidate] = []
    if remaining <= ceiling_chars:
        return chosen, remaining
    for candidate in drop_order(candidates, scores):
        if remaining <= ceiling_chars:
            break
        saving = candidate.chars - stub_length_bound(candidate, pointer_name, max_line)
        if saving <= 0:
            continue
        chosen.append(candidate)
        remaining -= saving
    return chosen, remaining


def verify_pointers(path: Path, pointers: list[dict]) -> list[dict]:
    """Re-read every pointer's line and confirm it names the record it claims.

    A pointer is a promise about a line in a file on disk.  This walks the file
    once, and for each promised line parses the record and checks the uuid (and
    the block's original character count) against what the pointer asserts.  Any
    discrepancy -- wrong line, moved record, unparseable line, missing line -- is
    returned as a mismatch, and the caller refuses to ship the output.
    """
    wanted: dict[int, list[dict]] = {}
    for pointer in pointers:
        wanted.setdefault(int(pointer["line"]), []).append(pointer)
    mismatches: list[dict] = []
    seen: set[int] = set()
    try:
        with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
            for number, raw in enumerate(handle, start=1):
                promised = wanted.get(number)
                if not promised:
                    continue
                seen.add(number)
                try:
                    record = json.loads(raw)
                except ValueError:
                    mismatches.append({"line": number, "reason": "unparseable"})
                    continue
                if not isinstance(record, dict):
                    mismatches.append({"line": number, "reason": "not-a-record"})
                    continue
                for pointer in promised:
                    if not pointer.get("names_line", True):
                        mismatches.append(
                            {"line": number, "key": pointer.get("key"), "reason": "no-line-number"}
                        )
                        continue
                    expected_uuid = pointer.get("uuid")
                    if expected_uuid is not None and record.get("uuid") != expected_uuid:
                        mismatches.append(
                            {
                                "line": number,
                                "key": pointer.get("key"),
                                "reason": "uuid-mismatch",
                                "expected": expected_uuid,
                                "found": record.get("uuid"),
                            }
                        )
                        continue
                    block_index = pointer.get("block_index")
                    message = record.get("message")
                    content = message.get("content") if isinstance(message, dict) else None
                    if block_index == -1 and isinstance(content, str):
                        # A whole-string record: measure the string itself.
                        if len(content) != int(pointer.get("chars", -1)):
                            mismatches.append(
                                {
                                    "line": number,
                                    "key": pointer.get("key"),
                                    "reason": "char-count-mismatch",
                                    "expected": int(pointer.get("chars", -1)),
                                    "found": len(content),
                                }
                            )
                        continue
                    if (
                        not isinstance(content, list)
                        or not isinstance(block_index, int)
                        or block_index >= len(content)
                        or not isinstance(content[block_index], dict)
                    ):
                        mismatches.append(
                            {"line": number, "key": pointer.get("key"), "reason": "block-missing"}
                        )
                        continue
                    # Measure the same text the compactor folded: a prose
                    # block's text and a tool call's arguments are not in
                    # ``content``, and counting them as zero would flag every
                    # honest prose pointer as a lie.
                    found_chars = len(block_text(content[block_index]))
                    if found_chars != int(pointer.get("chars", -1)):
                        mismatches.append(
                            {
                                "line": number,
                                "key": pointer.get("key"),
                                "reason": "char-count-mismatch",
                                "expected": int(pointer.get("chars", -1)),
                                "found": found_chars,
                            }
                        )
    except OSError:
        mismatches.append({"line": None, "reason": "source-unreadable"})
    for number in sorted(set(wanted) - seen):
        for pointer in wanted[number]:
            mismatches.append(
                {"line": number, "key": pointer.get("key"), "reason": "line-missing"}
            )
    return mismatches


def _stub_text(candidate: Candidate, text: str, line: int, name: str) -> str:
    return pointer_text(len(text), line, name)


# --------------------------------------------------------------------------
# pointers to indexes of pointers: grouped stubs, summarised by task
# --------------------------------------------------------------------------
#
# One stub per elided block costs about 100 characters each, and a long session
# elides thousands of blocks: the stubs themselves become a payload.  So a run of
# elisions that belongs to ONE task can be replaced by a single stub that points
# at a group in the index, which in turn lists the individual pointers.  Two
# rules make that safe and useful:
#
#   * a group stub is only used when it is genuinely cheaper than the individual
#     stubs it replaces (otherwise the finer pointer is strictly better);
#   * a group stub MUST carry a summary of what the group covers, by task and
#     project -- a bare group id is refused, because a pointer nobody can read is
#     worse than the text it replaced.

POINTER_GROUP_MAX_LABEL_CHARS = 88
POINTER_GROUP_MAX_SUMMARY_CHARS = 360
POINTER_GROUP_MIN_MEMBERS = 3
POINTER_GROUP_MIN_SAVING_CHARS = 400
POINTER_GROUP_TEMPLATE = (
    "[elided {count} blocks, {chars:,} chars \u2014 {label} \u2014 at line {line:,} of {name} "
    "through line {last:,}; group {gid} of {index}; {summary}]"
)
POINTER_GROUP_MEMBER_TEMPLATE = "[{gid} member: {chars:,} chars at line {line:,} of {name}]"
POINTER_GROUP_RE = re.compile(r"; group (g[\w-]+) of ")


SYNTHETIC_TURN_MARKERS = (
    "this session is being continued",
    "my reply to",
    "caveat: the messages below",
    "context compacted",
    "tool loaded",
    "stop hook feedback",
    "hook feedback",
    "system:",
    "base directory for this skill",
    "skill loaded",
    "working directory:",
)
# A task label must be long enough to name work.  Short interjections ("Yes",
# "Do it") answer the current task rather than starting a new one, so they keep
# the label they inherited instead of splitting a group in two.
TASK_LABEL_MIN_CHARS = 16


def _task_instruction(record: dict, max_chars: int) -> str:
    """The operator's instruction in this record, or "" when it is not one.

    A task label must be something a human said: continuation summaries, tool
    echoes and harness notes all arrive as ``user`` records, and labelling a
    group "This session is being continued..." would describe the bookkeeping
    instead of the work.
    """
    if record.get("isCompactSummary") or record.get("type") == "summary":
        return ""
    message = record.get("message")
    if not isinstance(message, dict) or message.get("role") != "user":
        return ""
    text = human_text(record).strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered.startswith(SYNTHETIC_TURN_MARKERS):
        return ""
    first = " ".join(text.splitlines()[0].split())
    if not first or first.startswith(("<", "[", "Caveat:")):
        return ""
    if first.endswith(":"):
        return ""
    if "/.claude/" in first or "/skills/" in first:
        return ""
    return first[:max_chars]


def task_labels(records: list[dict], max_chars: int = POINTER_GROUP_MAX_LABEL_CHARS) -> list[str]:
    """Label every record with the task it belongs to.

    A task starts at a human turn: the operator's own words are what define a
    unit of work, so the label is the first line of the most recent human message.
    Records before the first human turn carry no label, and their elisions stay
    ungrouped rather than being filed under a task nobody stated.
    """
    labels: list[str] = []
    current = ""
    for record in records:
        instruction = _task_instruction(record, max_chars)
        if instruction:
            # A short reply ("Yes", "Do it") answers the task it inherited; it
            # only becomes a label when there is nothing else to name.
            if len(instruction) >= TASK_LABEL_MIN_CHARS or not current:
                current = instruction
        labels.append(current)
    return labels


def _group_summary(count: int, chars: int, members: list[Candidate], texts: dict[str, str]) -> str:
    """A deterministic summary of what a group contains: no model, no guessing.

    What a reader needs from a summary is what the blocks WERE: which files they
    touched and how they began.  Both are read off the text itself, so the summary
    cannot drift from the content it describes.
    """
    paths: list[str] = []
    for candidate in members:
        for match in re.findall(r"(?:/[\w.+-]+){2,}", texts.get(candidate.key, "")[:2000]):
            if match not in paths:
                paths.append(match)
        if len(paths) >= 4:
            break
    heads: list[str] = []
    seen: set[str] = set()
    for candidate in members:
        first = next((line.strip() for line in texts.get(candidate.key, "").splitlines() if line.strip()), "")
        first = " ".join(first.split())[:60]
        if first and first not in seen:
            seen.add(first)
            heads.append(first)
        if len(heads) >= 2:
            break
    parts = ["{} blocks, {:,} chars".format(count, chars)]
    if paths:
        parts.append("files: " + ", ".join(paths[:4]))
    if heads:
        parts.append('begins: "' + '" / "'.join(heads) + '"')
    summary = "; ".join(parts)
    return summary[:POINTER_GROUP_MAX_SUMMARY_CHARS]


def build_pointer_groups(
    rows: list[tuple[int, dict]],
    chosen: list[Candidate],
    *,
    texts: dict[str, str],
    project: str = "",
    pointer_name: str = "source.jsonl",
    min_members: int = POINTER_GROUP_MIN_MEMBERS,
    min_saving_chars: int = POINTER_GROUP_MIN_SAVING_CHARS,
) -> tuple[list[dict], dict[str, tuple[str, str]]]:
    """Group elisions by task; collapse only the groups where that saves space.

    Returns (groups, plan).  ``plan`` maps a candidate key to ``(gid, role)``
    where role is ``"head"`` (the stub that carries the group's summary) or
    ``"member"``.  Candidates absent from ``plan`` keep their individual pointer,
    so a group that would cost more than it saves never appears.
    """
    labels = task_labels([record for _number, record in rows])
    number_by_position = {position: number for position, (number, _record) in enumerate(rows)}
    # A pointer must name the line in the file on disk, which is the row's own
    # number, never an index we recomputed from arithmetic.
    line_of: dict[str, int] = {
        candidate.key: int(number_by_position.get(candidate.position, 0)) for candidate in chosen
    }

    buckets: dict[str, list[Candidate]] = {}
    for candidate in chosen:
        label = labels[candidate.position] if candidate.position < len(labels) else ""
        buckets.setdefault(label, []).append(candidate)

    groups: list[dict] = []
    plan: dict[str, tuple[str, str]] = {}
    for label, members in buckets.items():
        if len(members) < max(2, int(min_members)):
            continue
        members = sorted(members, key=lambda c: (line_of.get(c.key, 0), c.block_index))
        chars = sum(candidate.chars for candidate in members)
        summary = _group_summary(len(members), chars, members, texts)
        if not summary or not summary.strip():
            # No summary, no group: a group stub must say what it covers.
            continue
        gid = "g{:02d}".format(len(groups) + 1)
        first_line = line_of.get(members[0].key, 0)
        last_line = line_of.get(members[-1].key, 0)
        head = POINTER_GROUP_TEMPLATE.format(
            count=len(members),
            chars=chars,
            label=label or "unlabelled task",
            line=first_line,
            name=pointer_name,
            last=last_line,
            gid=gid,
            index="index",
            summary=summary,
        )
        collapsed_cost = len(head) + sum(
            len(
                POINTER_GROUP_MEMBER_TEMPLATE.format(
                    gid=gid, chars=candidate.chars, line=line_of.get(candidate.key, 0), name=pointer_name
                )
            )
            for candidate in members[1:]
        )
        individual_cost = sum(
            len(pointer_text(candidate.chars, line_of.get(candidate.key, 0), pointer_name))
            for candidate in members
        )
        if individual_cost - collapsed_cost < int(min_saving_chars):
            continue
        group = {
            "gid": gid,
            "label": label,
            "project": project,
            "summary": summary,
            "chars": chars,
            "blocks": len(members),
            "first_line": first_line,
            "last_line": last_line,
            "members": [
                {
                    "key": candidate.key,
                    "line": line_of.get(candidate.key, 0),
                    "uuid": candidate.uuid,
                    "chars": candidate.chars,
                }
                for candidate in members
            ],
            "stub": head,
            "individual_cost": individual_cost,
            "collapsed_cost": collapsed_cost,
        }
        groups.append(group)
        plan[members[0].key] = (gid, "head")
        for candidate in members[1:]:
            plan[candidate.key] = (gid, "member")
    return groups, plan


def group_stub_for(gid: str, group: dict, member: Candidate, line: int, name: str) -> str:
    """The text written into an elided block that belongs to a collapsed group."""
    if group.get("stub") and group["members"] and group["members"][0]["key"] == member.key:
        return str(group["stub"])
    return POINTER_GROUP_MEMBER_TEMPLATE.format(gid=gid, chars=member.chars, line=line, name=name)


def group_id_in(text: str) -> str | None:
    """The group a stub CLAIMS, read out of the text itself."""
    match = POINTER_GROUP_RE.search(str(text))
    return match.group(1) if match else None


def verify_groups(index: "ElisionIndex", groups: list[dict]) -> list[dict]:
    """Every group stub must be expandable: the row exists and lists its members.

    A group stub is a promise that "group gNN of the index" can be opened.  If the
    group row is missing, or its member list is not exactly the set of blocks the
    stub swallowed, the promise is a lie and the pass must not ship.
    """
    mismatches: list[dict] = []
    for group in groups:
        gid = group["gid"]
        if not index.has_group(gid):
            mismatches.append({"gid": gid, "reason": "group-missing"})
            continue
        listed = {member["key"] for member in index.group_members(gid)}
        wanted = {member["key"] for member in group.get("members") or []}
        if listed != wanted:
            mismatches.append(
                {
                    "gid": gid,
                    "reason": "member-set-mismatch",
                    "missing": sorted(wanted - listed)[:5],
                    "extra": sorted(listed - wanted)[:5],
                }
            )
    return mismatches


# --------------------------------------------------------------------------
# the pass
# --------------------------------------------------------------------------


def compact(
    source: Path,
    out: Path,
    archive_dir: Path,
    *,
    keep_recent_records: int = DEFAULT_KEEP_RECENT_RECORDS,
    stub_over_chars: int = DEFAULT_STUB_OVER_CHARS,
    ceiling_tokens: int = DEFAULT_CEILING_TOKENS,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
    ranker: DeciderRanker | None = None,
    on_indexed=None,
    harness: dict | None = None,
    pointer_source: str | None = None,
    group_pointers: bool = False,
    fold_prose: bool = False,
    group_min_members: int = POINTER_GROUP_MIN_MEMBERS,
    group_min_saving_chars: int = POINTER_GROUP_MIN_SAVING_CHARS,
    project: str = "",
) -> CompactResult:
    """Compact a transcript COPY into ``out``; never mutates ``source``.

    ``ceiling_tokens`` is the COLD-RELOAD ceiling (70_000 by default) and
    ``harness`` is the measured baseline a resume pays before the conversation
    (see ``resolve_harness``).  The conversation is therefore allowed only
    ``ceiling - harness_tokens``; a total reload above the ceiling refuses.
    """
    source = Path(source).expanduser()
    out = Path(out).expanduser()
    archive_dir = Path(archive_dir).expanduser()
    harness_report = dict(harness or {})
    harness_tokens = max(0, int(harness_report.get("harness_tokens") or 0))
    conversation_budget_tokens = max(0, int(ceiling_tokens) - harness_tokens)
    pointer_name = str(pointer_source) if pointer_source else str(source)
    report: dict = {
        "schema": "dotcortex.offline-compact.v1",
        "source": str(source),
        "out": str(out),
        "archive": str(archive_dir),
        "ceiling_tokens": int(ceiling_tokens),
        "chars_per_token": float(chars_per_token),
        "tokenizer": tokenizer_label(chars_per_token),
        "token_estimate_basis": (
            "sum of message-text characters / chars_per_token; no provider tokenizer is invoked"
        ),
        "keep_recent_records": int(keep_recent_records),
        "stub_over_chars": int(stub_over_chars),
        "pointer_source": pointer_name,
        "harness_family": harness_report.get("harness_family"),
        "harness_scope": harness_report.get("harness_scope"),
        "harness_tokens": harness_tokens,
        "harness_chars": int(harness_report.get("harness_chars") or 0),
        "harness_index_tokens": int(harness_report.get("harness_index_tokens") or 0),
        "harness_source": harness_report.get("harness_source", "unaccounted:no-harness-supplied"),
        "harness_files": list(harness_report.get("harness_files") or []),
        "conversation_budget_tokens": conversation_budget_tokens,
    }

    if source.is_symlink() or not source.is_file():
        return CompactResult(False, "source-not-regular-file", report)
    if out == source:
        return CompactResult(False, "out-equals-source", report)
    if out.exists():
        return CompactResult(False, "out-exists", report)

    try:
        rows = load_records_with_lines(source)
        records = [record for _number, record in rows]
    except (OSError, ValueError) as error:
        report["error"] = type(error).__name__
        return CompactResult(False, "source-unreadable", report)

    try:
        chain_before, orphans = main_chain(records)
    except ChainError as error:
        report["chain_error"] = str(error)
        return CompactResult(False, "chain-broken-before", report)
    # A trailing orphan fragment is excluded from the working copy and reported
    # in full; the source file is never altered, so nothing is lost.
    excluded_positions = {item["position"] for item in orphans}
    report["orphans_excluded"] = orphans
    report["orphan_count"] = len(orphans)

    identities_before = identity_snapshot(records)
    human_before = [human_text(record) for record in records]
    non_context_chars = sum(
        len(json.dumps(record.get("message"))) if isinstance(record.get("message"), dict) else 0
        for record in records
        if not is_context_record(record)
    )
    report["non_context_chars_excluded"] = non_context_chars
    report["non_context_records_excluded"] = sum(1 for record in records if not is_context_record(record))
    chars_before = sum(
        all_text(record) for position, record in enumerate(records) if position not in excluded_positions
    )
    tokens_before = estimate_tokens(chars_before, chars_per_token)
    report.update(
        {
            "records": len(records),
            "chain_length": len(chain_before),
            "source_bytes": source.stat().st_size,
            "text_chars_before": chars_before,
            "est_tokens_before": tokens_before,
        }
    )

    candidates = elidable_candidates(
        records, keep_recent_records, stub_over_chars, include_prose=fold_prose
    )
    # The newest carried summary ("This session is being continued...") is the
    # one block that says what the work is. It stays verbatim: a pointer to it
    # would leave a resuming model with the last hour and not the week. Older
    # carried summaries are summaries of summaries and may become pointers.
    pinned_summary = newest_summary_position(records, excluded_positions)
    if pinned_summary is not None:
        candidates = [
            candidate
            for candidate in candidates
            if not (candidate.position == pinned_summary and candidate.block_index == -1)
        ]
    report["pinned_summary_position"] = pinned_summary
    report["elidable_candidates"] = len(candidates)
    report["fold_prose"] = bool(fold_prose)

    if candidates and ranker is not None:
        outcome = ranker.rank(candidates)
    else:
        outcome = RankOutcome(
            selector="fallback:no-decider-configured" if candidates else "fallback:no-candidates",
            status="unconfigured" if candidates else "empty",
        )
    report.update(
        {
            "selector": outcome.selector,
            "decider_status": outcome.status,
            "decider_endpoint": outcome.endpoint,
            "decider_latency_ms": outcome.latency_ms,
            "decider_answered": outcome.answered,
        }
    )
    scores = outcome.scores if outcome.usable else {}

    chosen, _projected = choose_elisions(
        candidates,
        chars_before,
        conversation_budget_tokens,
        float(chars_per_token),
        scores,
        pointer_name=pointer_name,
        max_line=len(rows) + 1,
    )
    chosen_keys = {candidate.key: candidate for candidate in chosen}
    report["selected_for_elision"] = len(chosen)

    # Grouping is decided BEFORE anything is written: the group's summary has to
    # exist in the index before the first block that points at it can lose its
    # text, exactly as with an individual pointer.
    groups: list[dict] = []
    groups_by_id: dict[str, dict] = {}
    group_plan: dict[str, tuple[str, str]] = {}
    group_mismatches: list[dict] = []
    if group_pointers and chosen:
        grouping_texts: dict[str, str] = {}
        for candidate in chosen:
            record = records[candidate.position] if candidate.position < len(records) else None
            message = record.get("message") if isinstance(record, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            part = None
            if isinstance(content, list) and 0 <= candidate.block_index < len(content):
                part = content[candidate.block_index]
            if isinstance(part, dict):
                grouping_texts[candidate.key] = block_text(part)
            elif candidate.block_index == -1 and isinstance(content, str):
                grouping_texts[candidate.key] = content
        groups, group_plan = build_pointer_groups(
            rows,
            chosen,
            texts=grouping_texts,
            project=project,
            pointer_name=pointer_name,
            min_members=group_min_members,
            min_saving_chars=group_min_saving_chars,
        )
        groups_by_id = {group["gid"]: group for group in groups}
    report["pointer_groups_offered"] = len(groups)

    index_dir = archive_dir / "index"
    try:
        index = ElisionIndex(index_dir)
    except (OSError, sqlite3.Error) as error:
        report["error"] = "index-open-failed:{}".format(type(error).__name__)
        return CompactResult(False, "index-open-failed", report, index_path=index_dir)

    elided = 0
    rewritten_positions: set[int] = set()
    pointers: list[dict] = []
    relocated_human: list[dict] = []
    folded_prose = 0
    try:
        # The group summaries exist before any block may point at them.
        for group in groups:
            index.add_group(group)
        with out.open("w", encoding="utf-8") as handle:
            for position, (line_number, record) in enumerate(rows):
                if position in excluded_positions:
                    continue
                message = record.get("message")
                content = message.get("content") if isinstance(message, dict) else None
                if isinstance(content, str):
                    candidate = chosen_keys.get("r{}-s".format(position))
                    if candidate is not None:
                        text = content
                        index.add(candidate.key, text, line_number)
                        if on_indexed is not None:
                            on_indexed(candidate.key, text)
                        planned = group_plan.get(candidate.key)
                        group_id = None
                        if planned:
                            group_id, _role = planned
                            stub = group_stub_for(
                                group_id, groups_by_id[group_id], candidate, line_number, pointer_name
                            )
                        else:
                            stub = _stub_text(candidate, text, line_number, pointer_name)
                        message["content"] = stub
                        folded_prose += 1
                        if message.get("role") == "user":
                            relocated_human.append(
                                {"key": candidate.key, "chars": len(text), "kind": "text"}
                            )
                        claimed_line = pointer_line(stub)
                        pointers.append(
                            {
                                "line": line_number if claimed_line is None else claimed_line,
                                "names_line": claimed_line is not None,
                                "record_line": line_number,
                                "uuid": candidate.uuid,
                                "block_index": -1,
                                "chars": len(text),
                                "key": candidate.key,
                                "group": group_id,
                            }
                        )
                        elided += 1
                        rewritten_positions.add(position)
                if isinstance(content, list):
                    for block_index, part in enumerate(content):
                        candidate = chosen_keys.get("r{}-{}".format(position, block_index))
                        if candidate is None or not isinstance(part, dict):
                            continue
                        text = block_text(part)
                        # 1. durable archive + FTS row, COMMITTED;
                        # 2. only then may the record lose the text.
                        index.add(candidate.key, text, line_number)
                        if on_indexed is not None:
                            on_indexed(candidate.key, text)
                        planned = group_plan.get(candidate.key)
                        group_id = None
                        if planned:
                            group_id, _role = planned
                            stub = group_stub_for(
                                group_id,
                                groups_by_id[group_id],
                                candidate,
                                line_number,
                                pointer_name,
                            )
                        else:
                            stub = _stub_text(candidate, text, line_number, pointer_name)
                        # The pointer goes back into the field that held the
                        # text (content / text / input), so the record still
                        # parses as the kind of block it was.
                        content[block_index] = staged_stub(part, stub)
                        kind = part.get("type")
                        if kind in PROSE_BLOCK_TYPES:
                            folded_prose += 1
                        # Only PROSE moves a human word: a tool_result in a
                        # user record is tool output, not something he typed.
                        if kind == "text" and isinstance(message, dict) and message.get("role") == "user":
                            relocated_human.append(
                                {"key": candidate.key, "chars": len(text), "kind": kind}
                            )
                        # The line the TEXT names, not the line we meant to name:
                        # verification must judge what the agent will actually
                        # read, so a stub that misstates its line is caught here.
                        claimed_line = pointer_line(stub)
                        pointers.append(
                            {
                                "line": line_number if claimed_line is None else claimed_line,
                                "names_line": claimed_line is not None,
                                "record_line": line_number,
                                "uuid": candidate.uuid,
                                "block_index": block_index,
                                "chars": len(text),
                                "key": candidate.key,
                                "group": group_id,
                            }
                        )
                        elided += 1
                        rewritten_positions.add(position)
                handle.write(json.dumps(record) + "\n")
                handle.flush()
        group_mismatches = verify_groups(index, groups) if groups else []
        relocated_missing = [
            item["key"] for item in relocated_human if index.body(item["key"]) is None
        ]
    except (OSError, sqlite3.Error) as error:
        try:
            out.unlink()
        except OSError:
            pass
        report["error"] = "elision-failed:{}".format(type(error).__name__)
        report["elided_blocks"] = 0
        return CompactResult(False, "index-or-write-failed", report, index_path=index_dir)
    finally:
        # Whatever happens above (including a bug in a caller hook), the index
        # handle is closed with the pass: a leaked sqlite handle here would
        # leave a journal behind in a directory the caller owns.
        try:
            index.close()
        except (OSError, sqlite3.Error):
            pass

    kept_records = [record for position, record in enumerate(records) if position not in excluded_positions]
    chars_after = sum(all_text(record) for record in kept_records)
    tokens_after = estimate_tokens(chars_after, chars_per_token)
    identities_after = identity_snapshot(records)
    human_changed = sum(
        1 for before, record in zip(human_before, records) if before != human_text(record)
    )
    # Every elision stub and group description must sit in a record the model
    # reads: a stub in a logging record is a pointer to nothing.  Only a record
    # THIS pass rewrote can hold such a stub.  A logging record that merely
    # quotes the stub text (a session that read this engine's source) was never
    # rewritten, and counting it made the pass refuse every such transcript.
    unreadable_stub_records = [
        position
        for position, record in enumerate(records)
        if position in rewritten_positions
        and position not in excluded_positions
        and not is_context_record(record)
        and "[elided" in json.dumps(record.get("message"))
    ]
    report["index_unreadable_records"] = unreadable_stub_records[:10]
    try:
        chain_after = parent_chain(kept_records)
    except ChainError as error:
        report["chain_error"] = str(error)
        chain_after = []

    # Every pointer is a promise about a line on disk: re-read it and check the
    # record it names.  A mismatch means the pointer lies, so nothing ships.
    verification_path = source
    verification_basis = "copy"
    if pointer_source:
        promised = Path(str(pointer_source)).expanduser()
        try:
            if promised.is_file() and not promised.is_symlink():
                verification_path = promised
                verification_basis = "pointer-source"
        except OSError:
            pass
    pointer_mismatches = verify_pointers(verification_path, pointers) if pointers else []
    mismatched_keys = {item.get("key") for item in pointer_mismatches}
    pointers_verified = sum(1 for pointer in pointers if pointer.get("key") not in mismatched_keys)

    total_reload_tokens = harness_tokens + tokens_after
    ceiling_met = (
        total_reload_tokens <= int(ceiling_tokens)
        and tokens_after <= conversation_budget_tokens
        and chars_after <= conversation_budget_tokens * float(chars_per_token)
    )
    report.update(
        {
            "elided_blocks": elided,
            "kept_verbatim": len(candidates) - elided,
            "text_chars_after": chars_after,
            "est_tokens_after": tokens_after,
            "total_reload_tokens": total_reload_tokens,
            "size_after_bytes": out.stat().st_size,
            "ceiling_met": ceiling_met,
            "ceiling_headroom_tokens": int(ceiling_tokens) - total_reload_tokens,
            "chain_length_after": len(chain_after),
            "human_words_changed": human_changed,
            "identity_preserved": identities_before == identities_after,
            "pointer_stubs": elided,
            "pointers_verified": pointers_verified,
            "pointer_mismatch_count": len(pointer_mismatches),
            "pointer_mismatches": pointer_mismatches[:10],
            "pointer_verification_basis": verification_basis,
            "index_path": str(index_dir),
            "index_entries": elided,
            "fold_prose": bool(fold_prose),
            "prose_blocks_folded": folded_prose,
            "human_blocks_relocated": len(relocated_human),
            "human_relocation_missing": relocated_missing[:10],
            "pointer_groups": len(groups),
            "pointer_group_blocks": sum(len(group.get("members") or []) for group in groups),
            "pointer_group_stub_chars": sum(len(str(group.get("stub", ""))) for group in groups),
            "pointer_group_saved_chars": sum(
                int(group.get("individual_cost") or 0) - int(group.get("collapsed_cost") or 0)
                for group in groups
            ),
            "group_mismatch_count": len(group_mismatches),
            "group_mismatches": group_mismatches[:10],
            "pointer_groups_detail": [
                {
                    "gid": group["gid"],
                    "label": group["label"],
                    "project": group["project"],
                    "summary": group["summary"],
                    "blocks": group["blocks"],
                    "chars": group["chars"],
                    "first_line": group["first_line"],
                    "last_line": group["last_line"],
                }
                for group in groups
            ],
        }
    )

    archive_dir.mkdir(parents=True, exist_ok=True)
    report_path = archive_dir / "compaction-report.json"
    report_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)

    reason = None
    if not report["identity_preserved"]:
        reason = "identity-not-preserved"
    elif human_changed and (relocated_missing or not fold_prose):
        # A human word may leave the working copy only by becoming an indexed
        # pointer: if the text is not byte-exact in the index, nothing ships.
        reason = "human-words-changed"
        try:
            out.unlink()
        except OSError:
            pass
    elif len(chain_after) != len(chain_before) or chain_after != chain_before:
        reason = "chain-changed"
    elif pointer_mismatches:
        # A pointer that names the wrong line is worse than no compaction: the
        # agent would be sent to text that is not its own.  Nothing ships.
        reason = "pointer-mismatch"
        try:
            out.unlink()
        except OSError:
            pass
    elif group_mismatches:
        # A group stub that the index cannot expand is a dead end: it says
        # "group g07" and there is no g07 to read.  Nothing ships.
        reason = "group-mismatch"
        try:
            out.unlink()
        except OSError:
            pass
    elif unreadable_stub_records:
        reason = "index-unreadable"
        try:
            out.unlink()
        except OSError:
            pass
    elif not ceiling_met:
        reason = "ceiling-not-met"
    elif elided == 0:
        reason = "no-elision-needed"
    return CompactResult(
        reason is None,
        reason,
        report,
        out_path=None if reason else out,
        index_path=index_dir,
    )


# --------------------------------------------------------------------------
# installation
# --------------------------------------------------------------------------


def rewrite_session_id(records: list[dict], session_id: str) -> list[dict]:
    for record in records:
        if "sessionId" in record:
            record["sessionId"] = session_id
    return records


def install_as_session(compacted: Path, project_dir: Path, session_id: str) -> Path:
    """Install a compacted copy as a new session file in the project slug dir.

    Records keep their uuid/parentUuid; only ``sessionId`` is rewritten so the
    CLI resumes the copy under the new id.  The file is 0600 and installed
    atomically; an existing session file is never overwritten.
    """
    if not isinstance(session_id, str) or not UUID4_RE.fullmatch(session_id):
        raise ValueError("session id must be a canonical uuid4: {!r}".format(session_id))

    project_dir = Path(project_dir).expanduser()
    if not project_dir.is_dir():
        raise FileNotFoundError("project directory does not exist: {}".format(project_dir))
    target = project_dir / "{}.jsonl".format(session_id)
    if target.exists():
        raise FileExistsError("refusing to overwrite an existing session: {}".format(target))

    records = rewrite_session_id(load_records(compacted), session_id)
    temporary = project_dir / ".{}.jsonl.tmp".format(session_id)
    fd = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    except BaseException:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    return target
