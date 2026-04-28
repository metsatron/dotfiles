---
name: pixelcortex-completion
description: Record a game completion in PixelCortex — log the finish, update analytics, honor the play, and cross-link to the system entry.
---

*description: Record a game completion in PixelCortex — log the finish, update analytics, honor the play, and cross-link to the system entry.*

> **Model:** `gpt-5.4` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# PixelCortex Completion

Use this skill when a game has been completed and the record needs to be formalized.

## Completion Files

| File | Purpose |
|------|---------|
| `completion/completion_log.md` | Master chronological log of all completions |
| `completion/honoring.md` | Games that received ceremonial completion — emotional weight, soul significance |
| `completion/analytics.md` | Aggregate statistics — platform counts, genre breakdowns, yearly totals |
| `completion/top10.md` | Curated top 10 lists |
| `completion/completionator-import-parsed.md` | Imported data from Completionator |

## Steps

### 1. Record the Completion

Add an entry to `completion/completion_log.md`:

```markdown
- **Game Title** — Platform — YYYY-MM-DD
  - Notes: any relevant context (first play, replay, modded, etc.)
```

### 2. Update the System Entry

Find the game in `systems/{platform}/{game-slug}.md` and update frontmatter:

```yaml
status: completed
date_completed: YYYY-MM-DD
```

Add a `## Completion` section if not present, with date and any final thoughts.

### 3. Honor Check

If the completion carries emotional weight or soul significance:
- Add to `completion/honoring.md` with a short paragraph about what the game meant.
- This is subjective and personal — write from Mètsàtron's voice, not corporate summary.

### 4. Update Analytics

Read `completion/analytics.md` and increment the relevant counters:
- Total completions
- Platform tally
- Genre tally (if tracked)
- Yearly count

### 5. Remove from Backlog

If the game appears in `backlog/sacred_canon.md` or `backlog/important_canon.md`, mark it as completed there (do not remove — strike through or annotate with completion date).

### 6. Cross-Link

Ensure the system entry, backlog entry, and completion log all reference each other.

## Rules

- Every completion gets a log entry. Not every completion gets an honoring entry — that requires genuine significance.
- Analytics are summaries of the log — the log is the source of truth.
- Never fabricate completion dates. If the exact date is unknown, use the best estimate and mark it `(approx)`.
- Honoring entries are prose, not data — write them with care.

