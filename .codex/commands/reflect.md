---
name: reflect
description: reflect - Manual Session Reflection
---

# reflect - Manual Session Reflection

Use this near a natural breakpoint when the session produced durable facts, reusable workflows, or OpenCode-layer improvements.

This is a manual OpenCode workflow, not a hook and not proof of automatic persistence.

## Steps

1. Summarize what happened in 2-4 lines.
2. Extract only durable items:
   - stable repo facts or tool behavior
   - user preferences confirmed by repeated behavior or explicit statements
   - reusable workflows or gotchas worth turning into a skill or command doc
   - wording changes that should update `.opencode/AGENTS.md` or `.opencode/README.md`
3. Keep session-specific scratch state out of durable files.
4. Write durable facts to `.opencode/memory/*.md` only when they remain useful across sessions.
5. If a reusable procedure emerged, prefer a new or updated `.opencode/skills/*/SKILL.md`, `.opencode/workflows/*.md`, or `.opencode/commands/*.md`.
6. If the discovery belongs in HelmCortex TODO tracking, mention the target file explicitly rather than assuming it should be written.

## Suggested Output Shape

```json
{
  "new_facts": [],
  "preference_updates": [],
  "skill_or_workflow_candidate": null,
  "opencode_layer_delta": null
}
```

## Rules

- never write to `.claude/MEMORY.md` from this workflow
- do not fabricate hooks, auto-save behavior, or slash-command discovery
- if the takeaway is procedural, prefer a skill or workflow over a memory note
- if nothing durable was learned, say so and stop
