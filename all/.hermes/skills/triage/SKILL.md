---
name: triage
description: Scan all tracking files and produce a compact TODO/research/evaluation health report.
---

*description: Scan all tracking files and produce a compact TODO/research/evaluation health report.*

> **Model:** `gpt-5.4-mini` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# /triage — TODO & Research Health Check

Scan all tracking files and produce a compact health report. No arguments needed.

## Steps

### 1. Read All TODO Files
Use `obsidian read` for each:
- `LOGS/TODO/HelmCortex.md`
- `LOGS/TODO/DotCortex.md`
- `LOGS/TODO/FontCortex.md`
- `LOGS/TODO/Machines/ThinkPad-X230.md`
- `LOGS/TODO/Machines/ThinkPad-T480s.md`

### 2. Read Research Index
Use `obsidian read path="LOGS/Research/README.md"`.

### 3. Scan Evaluation Scaffolds
Use `obsidian search query="Status:" path="LOGS/Antigravity/projects" limit=50` to enumerate evaluation docs, then `obsidian read` each to extract Status and date.

### 4. Check for Orphaned WebClippings
Use `obsidian search query="WebClipper" path="LOGS/WebClipper" limit=50` (or a broad query like `""`) to enumerate WebClipper files. For each, run `obsidian backlinks path="LOGS/WebClipper/<file>"` to check if it is referenced anywhere. Files with zero backlinks are orphans.

### 5. Produce Report

Output a compact report (under 50 lines) with these sections:

```
## TODO Health
| File | Open | Done | Stale (30d+) |
|------|------|------|--------------|

## Research Contamination
Items in TODO files that look like research (contain "Investigate", "Evaluate", "Explore", "Research"):
- <file>:<line> — "<item text>" → suggest: move to <destination>

## Evaluation Status
| Project | Layer | Status | Last Updated |
|---------|-------|--------|--------------|

## Stale Items (30+ days, no progress)
- <file> — "<item text>" (last progress: YYYY-MM-DD)

## Orphaned WebClippings
WebClippings in LOGS/WebClipper/ not linked from any evaluation or research doc.

```

### 6. Layer-Aware Staleness

Apply different staleness rules by layer:
- **Dionysus** items: soft completion criteria — flag at 60+ days, not 30
- **Hierem** items: concrete deliverables — flag at 30+ days

## Rules
- Report only, never auto-fix
- Keep output under 50 lines — summarize, don't enumerate every item
- If a section has zero findings, show it with "None" rather than omitting it
- Use the today's date for staleness calculations

