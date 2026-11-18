#!/usr/bin/env python3
"""Deterministic, provider-free compaction of a Claude session transcript copy.

This is the engine behind ``CLAUDE_IDLE_COMPACT_MODE=deterministic`` in
claude-warm.  It never calls a provider, never injects ``/compact`` and never
touches a live transcript: it reads a COPY, writes a new file, and archives plus
indexes every byte it elides BEFORE that byte leaves the context.

Policy (the same stub policy as FORGE/scripts/context_retention/compact_offline.py,
asserted against that tool by test-offline-compact-mode.py):

  * the last ``keep_recent_records`` records are untouched, whatever their size;
  * elsewhere, a ``tool_result`` block whose text exceeds ``stub_over_chars`` is
    replaced by a one-line stub;
  * user and assistant text is never modified, only tool output;
  * uuid, parentUuid, timestamps, types and record order are never touched.

Three rules the standalone tool's CLI cannot express, and that this path exists
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
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

STUB_TEMPLATE = "[tool output elided: {chars} chars, archived as {key}; first line: {first}]"

DEFAULT_CEILING_TOKENS = 70_000
DEFAULT_CHARS_PER_TOKEN = 4.0
DEFAULT_KEEP_RECENT_RECORDS = 60
DEFAULT_STUB_OVER_CHARS = 400
DEFAULT_DECIDER_BUDGET_MS = 2_500
DEFAULT_DECIDER_MAX_QUESTIONS = 24
DEFAULT_DECIDER_EXCERPT_CHARS = 600

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


def text_of_part(part: dict) -> str:
    content = part.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(x.get("text", "") for x in content if isinstance(x, dict))
    return ""


def all_text(record: dict) -> int:
    """Every character of message text in this record, tool output included."""
    message = record.get("message")
    if not isinstance(message, dict):
        return 0
    content = message.get("content")
    if isinstance(content, str):
        return len(content)
    total = 0
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                if isinstance(part.get("text"), str):
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


def load_records(path: Path) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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
        self.connection.commit()
        fd = os.open(self.index_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        self.journal = os.fdopen(fd, "a", encoding="utf-8")
        self.count = 0

    def add(self, key: str, body: str) -> str:
        """Archive and index one block; returns its sha256."""
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.journal.write(json.dumps({"key": key, "sha256": digest, "chars": len(body)}) + "\n")
        self.journal.flush()
        os.fsync(self.journal.fileno())
        self.connection.execute(
            "INSERT INTO elided(key, sha256, chars, body) VALUES (?, ?, ?, ?)",
            (key, digest, len(body), body),
        )
        self.connection.commit()
        self.count += 1
        return digest

    def search(self, query: str, limit: int = 10) -> list[str]:
        rows = self.connection.execute(
            "SELECT key FROM elided WHERE elided MATCH ? LIMIT ?", (query, limit)
        ).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        try:
            self.connection.close()
        finally:
            try:
                self.journal.close()
            except OSError:
                pass


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
) -> list[Candidate]:
    boundary = max(0, len(records) - max(0, keep_recent_records))
    found: list[Candidate] = []
    for position, record in enumerate(records[:boundary]):
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block_index, part in enumerate(content):
            if not isinstance(part, dict) or part.get("type") != "tool_result":
                continue
            text = text_of_part(part)
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


def stub_length_bound(candidate: Candidate) -> int:
    """Upper bound on a stub's length for this candidate.

    The first line is capped at 120 chars by ``_stub_text``, so this bound is
    exact enough for the ceiling arithmetic below and never under-counts.
    """
    return len(STUB_TEMPLATE.format(chars=candidate.chars, key=candidate.key, first="x" * 120))


def choose_elisions(
    candidates: list[Candidate],
    chars_before: int,
    ceiling_tokens: int,
    chars_per_token: float,
    scores: dict[str, float] | None,
) -> tuple[list[Candidate], int]:
    """Elide lowest-relevance candidates until the ceiling is met.

    Returns (chosen, chars_after).  Comparison happens in characters (the unit
    actually measured) so rounding never hides a breach of the ceiling.
    """
    ceiling_chars = ceiling_tokens * chars_per_token
    remaining = chars_before
    chosen: list[Candidate] = []
    if remaining <= ceiling_chars:
        return chosen, remaining
    for candidate in drop_order(candidates, scores):
        if remaining <= ceiling_chars:
            break
        saving = candidate.chars - stub_length_bound(candidate)
        if saving <= 0:
            continue
        chosen.append(candidate)
        remaining -= saving
    return chosen, remaining


def _stub_text(candidate: Candidate, text: str) -> str:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")[:120]
    return STUB_TEMPLATE.format(chars=len(text), key=candidate.key, first=first)


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
) -> CompactResult:
    """Compact a transcript COPY into ``out``; never mutates ``source``."""
    source = Path(source).expanduser()
    out = Path(out).expanduser()
    archive_dir = Path(archive_dir).expanduser()
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
    }

    if source.is_symlink() or not source.is_file():
        return CompactResult(False, "source-not-regular-file", report)
    if out == source:
        return CompactResult(False, "out-equals-source", report)
    if out.exists():
        return CompactResult(False, "out-exists", report)

    try:
        records = load_records(source)
    except (OSError, ValueError) as error:
        report["error"] = type(error).__name__
        return CompactResult(False, "source-unreadable", report)

    try:
        chain_before = parent_chain(records)
    except ChainError as error:
        report["chain_error"] = str(error)
        return CompactResult(False, "chain-broken-before", report)

    identities_before = identity_snapshot(records)
    human_before = [human_text(record) for record in records]
    chars_before = sum(all_text(record) for record in records)
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

    candidates = elidable_candidates(records, keep_recent_records, stub_over_chars)
    report["elidable_candidates"] = len(candidates)

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
        candidates, chars_before, int(ceiling_tokens), float(chars_per_token), scores
    )
    chosen_keys = {candidate.key: candidate for candidate in chosen}
    report["selected_for_elision"] = len(chosen)

    index_dir = archive_dir / "index"
    try:
        index = ElisionIndex(index_dir)
    except (OSError, sqlite3.Error) as error:
        report["error"] = "index-open-failed:{}".format(type(error).__name__)
        return CompactResult(False, "index-open-failed", report, index_path=index_dir)

    elided = 0
    try:
        with out.open("w", encoding="utf-8") as handle:
            for position, record in enumerate(records):
                message = record.get("message")
                content = message.get("content") if isinstance(message, dict) else None
                if isinstance(content, list):
                    for block_index, part in enumerate(content):
                        candidate = chosen_keys.get("r{}-{}".format(position, block_index))
                        if candidate is None or not isinstance(part, dict):
                            continue
                        text = text_of_part(part)
                        # 1. durable archive + FTS row, COMMITTED;
                        # 2. only then may the record lose the text.
                        index.add(candidate.key, text)
                        if on_indexed is not None:
                            on_indexed(candidate.key, text)
                        stub = _stub_text(candidate, text)
                        content[block_index] = {
                            key: value for key, value in part.items() if key != "content"
                        }
                        content[block_index]["content"] = stub
                        elided += 1
                handle.write(json.dumps(record) + "\n")
                handle.flush()
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

    chars_after = sum(all_text(record) for record in records)
    tokens_after = estimate_tokens(chars_after, chars_per_token)
    identities_after = identity_snapshot(records)
    human_changed = sum(
        1 for before, record in zip(human_before, records) if before != human_text(record)
    )
    try:
        chain_after = parent_chain(records)
    except ChainError as error:
        report["chain_error"] = str(error)
        chain_after = []

    ceiling_met = (
        tokens_after <= int(ceiling_tokens)
        and chars_after <= int(ceiling_tokens) * float(chars_per_token)
    )
    report.update(
        {
            "elided_blocks": elided,
            "kept_verbatim": len(candidates) - elided,
            "text_chars_after": chars_after,
            "est_tokens_after": tokens_after,
            "size_after_bytes": out.stat().st_size,
            "ceiling_met": ceiling_met,
            "ceiling_headroom_tokens": int(ceiling_tokens) - tokens_after,
            "chain_length_after": len(chain_after),
            "human_words_changed": human_changed,
            "identity_preserved": identities_before == identities_after,
            "index_path": str(index_dir),
            "index_entries": elided,
        }
    )

    archive_dir.mkdir(parents=True, exist_ok=True)
    report_path = archive_dir / "compaction-report.json"
    report_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)

    reason = None
    if not report["identity_preserved"]:
        reason = "identity-not-preserved"
    elif human_changed:
        reason = "human-words-changed"
    elif len(chain_after) != len(chain_before) or chain_after != chain_before:
        reason = "chain-changed"
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
