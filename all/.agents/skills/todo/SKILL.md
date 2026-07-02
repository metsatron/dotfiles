---
name: todo
description: DotCortex Task Routing
model: claude-haiku-4-5-20251001
---

# DotCortex Task Routing

Use this to route and update DotCortex TODO items.

## Rules

- Use Obsidian Tasks format.
- Keep TODO files action-oriented, not research-shaped.
- Route concrete tasks to the right HelmCortex TODO page when the work belongs there.
- Mark individual completed tasks in place with `[x] ... ✅ YYYY-MM-DD`.
- Move content to `LOGS/TODO/closed/` only when an entire task block is complete; never move isolated done items out of an otherwise-active block.
- Never delete completed task history; when a full block is closed, move the block intact to the matching closed ledger.
- Do not create timestamped backup files inside Obsidian/HelmCortex TODO trees. They pollute the vault. Use the TODO repo's Git state for rollback safety: check status, stage the exact dirty TODO file before editing when needed, and inspect the diff afterward.
