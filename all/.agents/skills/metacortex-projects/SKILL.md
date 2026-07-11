---
name: metacortex-projects
description: Navigate and manage MetaCortex project plans — structure, frontmatter, build sequences, README index, and project vs evaluation scope.
---

# MetaCortex Projects

Use this skill when creating, updating, or navigating project plans in MetaCortex.

## Location

MetaCortex lives at: `~/HelmCortex/CORTEX/GoldenAge_Loom/MetaCortex/`

```
MetaCortex/
  Projects/       ← things WE BUILD (this skill's domain)
  Evaluations/    ← external tools/projects assessed for integration
  Research/       ← landscape docs, synthesis, cross-cutting analysis
  Investigations/
  Audits/
  Debugging/
  README.md       ← project index — always update when adding a project
```

## Project vs Evaluation

- **Projects** — things being built by Mètsàtron. Tracked in `Projects/`.
- **Evaluations** — external tools assessed for integration (Five Pillars protocol). Tracked in `Evaluations/`.

## File Layout

**Single-file project** (contained scope):
```
Projects/Name.md
```

**Multi-file project** (broad scope):
```
Projects/Name/
  index.md          ← entry point: vision, build sequence, sub-note links
  Sub-Topic-A.md
  Sub-Topic-B.md
```

## Frontmatter Template

```yaml
---
title: Project Name
date: 'YYYY-MM-DD'
tags:
  - project
  - relevant-tag
aliases:
  - Alternative Name
---
```

## Common Sections

```markdown
# Project Name

> One-line vision statement.

**Conceived:** date and source conversation/session.

---

## Context / Vision

## Architecture

## Build Sequence

Phase 0 — Prerequisite
  □ Step A
  □ Step B

Phase 1 — First deliverable
  □ Step C
  ✓ Step D (done)

## Sub-notes (for multi-file projects)
- [[Sub-Topic-A]] — description
- [[Sub-Topic-B]] — description
```

## Adding a New Project

1. Create `Projects/Name.md` or `mkdir Projects/Name/` + `index.md`
2. Write content with frontmatter + standard sections
3. Add to `README.md` under `## Projects`:
   ```markdown
   - [[Projects/Name/index|Name]] — one-line description
   ```

## Existing Projects (as of 2026-06-20)

- [[AI-Sessions]] — cross-machine agent session indexer
- [[Fleet-Log-Capture/index]] — fleet-wide agent-log capture pipeline
- [[Prompt-Golf]] — token-constrained project management
- [[Session-Scanner]] — session tail scanner and classifier
- [[Synapse-Daemon]] — Obsidian co-occurrence indexer
- [[Monolithic-Emitter]] — unified AI session emitter pipeline
- [[ChronoNebula-Academy]] — temporal tracking and Vedic calendar
- [[Virtual-Habitat/index]] — VM/container habitat: Distrobox rooms, Azure Neptune KVM, historical Unix fleet

## Creating Notes

Prefer direct file writes (`Write` tool) for new notes. Use `obsidian-cli` only when live vault state is needed (backlinks, search, tasks via the running app).
