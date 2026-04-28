---
name: pixelcortex-backlog
description: Manage PixelCortex backlog vows — add, promote, or complete games in sacred canon, important canon, and wishlist.
---

*description: Manage PixelCortex backlog vows — add, promote, or complete games in sacred canon, important canon, and wishlist.*

> **Model:** `gpt-5.4` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# PixelCortex Backlog

Use this skill when managing the backlog system: vows, wishlists, and completion tracking.

## Vow Tiers

| File | Tier | Rule |
|------|------|------|
| `backlog/sacred_canon.md` | Soulbound | Must-finish before death. Never demote without Mètsàtron's explicit instruction. |
| `backlog/important_canon.md` | High priority | Intended completion, flexible timeline. |
| `backlog/wishlist.md` | Wishlist | Unacquired games of interest. |
| `backlog/mods.md` | Mod backlog | Games awaiting mod installation or configuration. |

## Workflow

### Adding a Vow

1. Read the target file.
2. Insert the game under the appropriate section.
3. Sacred canon entries must include the platform and any relevant notes (e.g. "heavily modded", "legacy save").
4. Never add to sacred canon without Mètsàtron's confirmation — this is a soul contract.

### Completing a Vow

1. Mark the game as done in the backlog file.
2. Add the completion record to `completion/completion_log.md` with date and platform.
3. If the game received ceremonial completion (emotional significance, milestone), add to `completion/honoring.md`.
4. Update the game's system entry with `status: completed` and `date_completed`.
5. Update `completion/analytics.md` aggregate counters.

### Promoting / Demoting

- **Promote**: wishlist → important canon → sacred canon. Each promotion requires reading the current file and moving the entry.
- **Demote**: sacred canon → important canon. **Requires Mètsàtron's explicit instruction.** Never auto-demote from soulbound tier.
- Stale entries (3+ years with zero progress) may be flagged but never removed.

## Rules

- Sacred canon is inviolable — treat it as a covenant.
- Completion entries must include the date.
- Analytics are derived, not primary — always update the log first, then analytics.
- `backlog/archive.md` holds retired vows — never delete, always archive.

