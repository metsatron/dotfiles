---
name: lightcone
description: Manage the LightCone section of HelmCortex TODO files — curate Active/Pending items, flush closed blocks, and sync with PromptGolf hole state.
---

*description: Manage the LightCone section of HelmCortex TODO files — curate Active/Pending items, flush closed blocks, and sync with PromptGolf hole state.*

> **Model:** `gpt-5.4` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# /lightcone — Attention Focus System

The LightCone is the curated top section of each scope TODO file. It defines what is **causally in reach right now** — the narrow window injected into session context at boot. Everything outside it is history or backlog.

## Structure

```markdown
## LightCone

### Active
- [ ] item in play this session or next (1–3 items max)

### Pending
- [ ] next priority, becomes Active when Active clears (2–3 items max)
```

**Active** — being worked in this or the next session. Maps to PromptGolf holes with `lie: fairway / rough / bunker / green`.  
**Pending** — explicitly queued next. Maps to PromptGolf holes in `queued/` state.  
**Backlog** — everything else. Lives below the LightCone separator in the same file. Not injected.

## Scope Files

| Scope | TODO file |
|-------|-----------|
| `helm` | `LOGS/TODO/HelmCortex.md` |
| `forge` | `LOGS/TODO/FORGE.md` |
| `bridge` | `LOGS/TODO/bridge.md` |
| `dot` | `LOGS/TODO/DotCortex.md` |
| `auryn` | `LOGS/TODO/my_brain_auryn.md` |
| `t480s` | `LOGS/TODO/Machines/ThinkPad-T480s.md` |
| `x230` | `LOGS/TODO/Machines/ThinkPad-X230.md` |

Injection: `claude-hook-session-start` reads `LOGS/TODO/$WORKSPACE.md` and `LOGS/TODO/Machines/$HOSTNAME.md` on every session open. The LightCone section is at the top, so it lands first in injected context.

## Closed Items

Done Progress blocks flush to `LOGS/TODO/closed/{scope}.md`.  
Rule: flush when a Progress block is fully checked AND the date is 30+ days old.  
Never delete — always move to `closed/`.

## PGA Tour Contract

LightCone and PromptGolf hole state must stay consistent:

- `prompt-golf tee-off` opens a new hole → add it to **Pending** in the relevant scope lightcone
- Hole moves from queued → active (swing started) → promote it to **Active**
- Hole closes (`lie: hole`) → mark item done, flush the completed block to `closed/` on next flush

## Subcommands

### `show [scope]`
Display the LightCone section for the given scope (default: current workspace).

Read with `obsidian read path="LOGS/TODO/<file>"` and extract from `## LightCone` to the next `## ` heading. Haiku-tier: mechanical read only.

### `add <scope> <section> <item>`
Add an item to Active or Pending.

1. Read the file with `obsidian read`
2. Insert under `### Active` or `### Pending` using the `Edit` tool
3. Enforce caps: Active max 3, Pending max 3
4. If a section is at cap, demote the lowest item before adding — ask before demoting

### `promote <search text>`
Move an item up one level: Backlog → Pending, or Pending → Active.

1. Search for the item with `obsidian search`
2. Read the file, identify current section
3. Move up one level, enforce caps (ask before displacing)

### `demote <search text>`
Move an item down one level: Active → Pending, or Pending → Backlog.

### `flush [scope]`
Move completed Progress blocks to `closed/`.

1. Read the scope TODO file
2. Find `## Progress — YYYY-MM-DD` blocks where ALL items are `[x]` and date is 30+ days old
3. Append to `LOGS/TODO/closed/{scope}.md`
4. Remove flushed blocks from the source file
5. Report what moved

### `sync`
Reconcile LightCone with PromptGolf hole state for the current course.

1. Read `ROOTS/PromptGolf/courses/{course}/holes/{active,queued}/` JSON files
2. Compare active holes against LightCone `### Active`, queued holes against `### Pending`
3. Report discrepancies: holes active in PromptGolf but absent from Active; items in Active with no corresponding hole
4. Propose reconciliation — never auto-apply without confirmation

## Rules
- LightCone is curated, not exhaustive — hard cap 3 Active, 3 Pending
- Never add to Active something that won't be touched this session or next
- Items that slip 3+ sessions without progress → demote to Backlog without ceremony
- `lightcone sync` at the start of any PGA Tour session
- `todo add` routes to Backlog by default — use `lightcone add` to target Active/Pending explicitly

