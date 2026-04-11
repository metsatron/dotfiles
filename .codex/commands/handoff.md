---
name: handoff
description: handoff - DotCortex Session Summary
---

# handoff - DotCortex Session Summary

Use this when a DotCortex session should be resumed in a fresh window.

## Steps

1. Review work completed, decisions made, and commands that matter
2. Run:
   - `git log --oneline -10`
   - `git status --short`
   - `git diff --stat`
3. Update the relevant canonical TODO file in `~/HelmCortex/LOGS/TODO/` with a dated progress block if meaningful work was completed
4. Write a concise handoff note somewhere the user wants to continue from later
5. Include fresh verification evidence if any command results support the current state

## Suggested Structure

```md
# Handoff - YYYY-MM-DD HH:MM

## Work Completed
- ...

## Commits This Session
- hash: message

## Decisions Made
- ...

## Open Threads
- ...

## Key Files Touched
- path - note

## Uncommitted Changes
- clean / summary
```

## Rules

- Keep it short and practical
- Focus on what a fresh session needs, not the full transcript
- Mention whether org sources were changed and whether `make tangle` or stow/apply commands were run
- Mention which TODO file in `~/HelmCortex/LOGS/TODO/` was updated, or explicitly note if no TODO update was needed
- Do not imply something was verified unless the handoff includes the actual fresh command evidence
