---
name: claude-session-logs
description: Locate and resume exported Claude Code session logs in the canonical HelmCortex .MASTER corpus. Use when asked to find the newest Claude session, recover a continuation point, or search an exported Claude transcript.
model: claude-haiku-4-5-20251001
---

# Claude Session Log Retrieval

Use the exported Claude Code Markdown corpus in HelmCortex. Do not search the home
directory, Claude runtime state, Downloads, or unrelated LOGS trees to find an export.

## Canonical DotCortex Export Scope

```text
/home/metsatron/mnt/x230/HelmCortex/LOGS/Claude/Code/.MASTER/ThinkPad-T480s/metsatron/dotcortex/
```

The hierarchy below `.MASTER` is:

```text
<machine>/<user>/<project>/<YYYY-MM>/<session-title>.md
```

## Workflow

1. Start at the canonical `.MASTER/<machine>/<user>/<project>/` directory.
2. Find the most recently modified regular file only within that project scope:
   ```bash
   find '<project-scope>' -type f -printf '%T@ %p\n' | sort -nr | head
   ```
3. Search the newest candidates for the user's quoted continuation anchor with `rg -n -F`.
4. If exact matching fails, search distinctive fragments with `rg -n -i -C 8`.
5. Read enough surrounding context to identify the last completed action and next action.
6. Report the exact file and matching line before continuing work.

## Hard Rules

- Never launch an unbounded search across `/home/metsatron` or `$HOME` for exported sessions.
- Never guess another export directory when the canonical scope is unavailable.
- If machine, user, or project scope cannot be determined from the request or current workspace,
  ask Mètsàtron for the exact scope before searching.
- A date embedded in a filename is not proof of recency; order candidates by modification time.
- `.MASTER` is the monolithic exported-session corpus. Keep searches inside its relevant project subtree.
