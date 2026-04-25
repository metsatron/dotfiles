---
name: session-wrap
description: Close out a work session cleanly with handoff, TODO, doc, and memory hygiene.
---

*description: Close out a work session cleanly with handoff, TODO, doc, and memory hygiene.*

> **Model:** `gpt-5.4-mini` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# /session-wrap — Closeout Hygiene

Umbrella closeout command for ending a HelmCortex work session cleanly.

Use this near a session boundary when you want to preserve continuity without
turning memory or documentation into empty ritual.

This is wider than `/handoff`. It can trigger commit, handoff, and reflect in one pass
so the user doesn't have to invoke each separately.

## Workflow

1. Review current `git status`, recent commits, and files changed in the session.
2. Decide whether the current work should be checkpointed with a commit — if so, ask and run `/commit`.
3. Review TODO state and record any real follow-up work in `LOGS/TODO/`.
4. Identify docs or notes that became stale because of the work.
5. Write a handoff via `/handoff` only if a fresh window will likely continue the task.
6. Invite `/reflect` only if something genuinely crystallized.

## Checklist

- commit-ready changes that should be preserved before stopping
- unrelated unstaged or uncommitted work that may have been forgotten
- follow-up tasks that belong in `LOGS/TODO/`
- docs that are now stale because of this session's work
- unresolved risks or missing verification steps
- reusable lessons worth a `/reflect` pass

## Commit Gate

- If there is meaningful uncommitted work, ask whether to run `/commit` first.
- If the user does not want a commit, capture the uncommitted state honestly and continue closeout.
- Do not commit silently just because session-wrap is being used.

## Relationship To Other Commands

- Use `/handoff` when the main goal is resumability in a fresh session.
- Use `/reflect` when the main goal is extracting durable learning.
- Use `/session-wrap` when you want one closeout pass that can trigger either of those if needed.

## Rules

- Do not fabricate learning just to fill a closeout ritual.
- Do not write memory entries for ordinary churn.
- Prefer a compact, useful handoff over exhaustive diary prose.
- Review TODO state even if no handoff is needed.
- If a commit would help preserve the current state, ask about it instead of assuming.
- If nothing needs wrapping, say so and stop.

