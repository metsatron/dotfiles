---
name: todo
description: DotCortex Task Routing
---

# DotCortex Task Routing

Use this to route and update TODO items in `~/HelmCortex/LOGS/TODO/`. Every TODO file has two zones with DIFFERENT laws: the `## LightCone` section (loaded into every session's context by the session-start hook) and the body (everything below it). Know which zone you are editing before you edit.

## Zone 1 — the LightCone: focus, never a dumping ground

The LightCone answers exactly one question: "what is in focus RIGHT NOW?" It is not the inbox, not the backlog, not the ledger. Hard limits — check them EVERY time you touch a TODO file, even if you only came to add one item:

1. `### Active` holds AT MOST 5 open items. The ideal is 3.
2. NO `[x]` item may remain anywhere inside the LightCone. Completed means moved out in the same edit (see Completion law).
3. The whole `## LightCone` section stays under 6000 bytes. Verify after editing: `awk '/^## LightCone/{p=1} p && /^## / && !/^## LightCone/{exit} p' <file> | wc -c`
4. The LightCone contains no `### Pending` or other holding pens — only `### Active`. Anything not in focus lives in `## Backlog` in the body.
5. If any limit is already broken when you arrive (by whoever came before), triage BEFORE your other work: keep the genuinely-in-focus items in `### Active`, move every other open item to `## Backlog`. Do not walk past an over-cap LightCone — the session-start hook flags it to every session until someone fixes it, and that someone is you.

Routing a NEW item:
- Default destination is `## Backlog` (create it directly after the LightCone section if missing). Filing into the LightCone is the exception, not the norm.
- An item enters `### Active` ONLY if it is being worked now or next AND a slot is free. If the user says it displaces something, demote the displaced item to `## Backlog` in the same edit.

## Zone 2 — the body: blocks, history, closure

- Mark a completed task in place first: `[x] ... ✅ YYYY-MM-DD`.
- **Completion law (LightCone)**: if the completed task lives in the LightCone, move the checked line OUT in the same edit, into a `## Progress — YYYY-MM-DD (<session>)` section in the same file. This is the deliberate exception to the don't-move rule below — the LightCone never accumulates history.
- **Don't-move rule (body)**: elsewhere, leave `[x]` items in place inside their block; never move isolated done items out of an otherwise-active block.
- **Chain-closure law**: when EVERY task in a chain/block is `[x]`, the chain is DONE and must leave the TODO file in the same session — move the whole block intact to the matching ledger under `LOGS/TODO/closed/` (same relative path as the source: `closed/DotCortex.md`, `closed/Machines/ThinkPad-T480s.md`; create the ledger if missing, append under `## Closed YYYY-MM-DD — <block title>`). Never leave a fully-completed block sitting in a TODO file, and never delete history — closed means moved, not erased.

## General rules

- Use Obsidian Tasks format; every task is ONE unwrapped line.
- Keep TODO files action-oriented, not research-shaped.
- Route concrete tasks to the right page: machine-specific work → `LOGS/TODO/Machines/<machine-file>.md`, workspace work → the workspace page. When in doubt, the page whose LightCone should surface it.
- Do not create timestamped backup files inside Obsidian/HelmCortex TODO trees. They pollute the vault. Use the TODO repo's Git state for rollback safety: check status, stage the exact dirty TODO file before editing when needed, inspect the diff afterward, and commit by pathspec.
