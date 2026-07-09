---
name: claude-session-logs
description: Locate and resume exported Claude Code session logs in the canonical HelmCortex .MASTER corpus. Use when asked to find the newest Claude session, recover a continuation point, or search an exported Claude transcript.
model: claude-haiku-4-5-20251001
---

# Claude Session Log Retrieval

Use the exported Claude Code Markdown corpus in HelmCortex first. If the user gives a
session ID and the export is missing or stale, fall back to the matching live Claude
project JSONL at `~/.claude/projects/<project>/<session-id>.jsonl` or
`~/.claude/projects/<session-id>.jsonl` if present. Do not search the home directory
blindly, and do not roam unrelated LOGS trees.

## Canonical DotCortex Export Scope

```text
/home/metsatron/mnt/x230/HelmCortex/LOGS/Claude/Code/.MASTER/ThinkPad-T480s/metsatron/dotcortex/
```

The hierarchy below `.MASTER` is:

```text
<machine>/<user>/<project>/<YYYY-MM>/<session-title>.md
```

## `rg` Will Silently Find Nothing Without `-uu`

`.MASTER` lives under `LOGS/`, which is git-ignored. `rg` honours ignore files by default, so
a plain `rg pattern <scope>` searches the export corpus and returns **zero hits** — not an
error, just silence indistinguishable from a genuine absence. Every search in this skill must
pass `-uu` (`--no-ignore --hidden`). If a search of the corpus comes back empty, re-run it with
`-uu` before concluding anything is missing.

## Workflow

1. Start at the canonical `.MASTER/<machine>/<user>/<project>/` directory.
2. Find the most recently modified regular file only within that project scope:
   ```bash
   find '<project-scope>' -type f -printf '%T@ %p\n' | sort -nr | head
   ```
3. If a session ID is available, search the exported corpus for `session_id: <id>` first,
   with `rg -uu -n -F 'session_id: <id>'`.
4. If the export is missing or stale, inspect the exact live JSONL path for that session
   under `~/.claude/projects` and use it as the source of truth for resuming.
5. When opening an exported transcript, verify its YAML front matter includes
   `session_id:`. If that field is missing, treat the export as incomplete and use the
   live JSONL source for the session instead.
6. Search the newest candidates for the user's quoted continuation anchor with `rg -uu -n -F`.
7. If exact matching fails, search distinctive fragments with `rg -uu -n -i -C 8`.
8. Read enough surrounding context to identify the last completed action and next action.
9. Report the exact file and matching line before continuing work.

## Hard Rules

- Never launch an unbounded search across `/home/metsatron` or `$HOME` for exported sessions.
- Never guess another export directory when the canonical scope is unavailable.
- Never invent a session path; only use the exact session ID to resolve the exact JSONL
  file under `~/.claude/projects` when export lag is the issue.
- If machine, user, or project scope cannot be determined from the request or current workspace,
  ask Mètsàtron for the exact scope before searching.
- A date embedded in a filename is not proof of recency; order candidates by modification time.
- `.MASTER` is the monolithic exported-session corpus. Keep searches inside its relevant project subtree.
- Never search the corpus without `-uu`. An empty `rg` result over a git-ignored tree is
  evidence of nothing. Never report a session as absent on the strength of a bare `rg`.
- A session's title is a fossil of its first message, not a description of its contents. Long
  sessions drift far from where they opened, so never rule a candidate out on its title or
  filename slug — grep the bodies. Search by artifact instead: the file the session wrote, the
  invoice number, the hostname, an exact phrase the user remembers.
- Corroborate the session against the working tree. Modification times on the files a session
  produced, and `git status` for what it left uncommitted, will pin the right transcript faster
  than title-matching and will confirm you found the right one.
