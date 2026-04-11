---
name: loom
description: loom - Loom-First Routing Convention
---

# loom - Loom-First Routing Convention

Use this when the task explicitly mentions `/loom`, Loom verbs, tangle, stow, or DotCortex package application.

`/loom` is not a fixed workflow like `/todo` or `/handoff`. It is a routing convention that means: interpret the rest of the request through DotCortex's Loom control plane.

## Usage

- `/loom`
- `/loom npm:apply`
- `/loom stow:t480s`

Arguments are optional. If a verb is provided, use it directly. If no verb is provided, infer the right Loom-aware action from the rest of the request.

## Steps

1. Load `.opencode/skills/dotcortex-loom/SKILL.md`.
2. Treat `loom.org` as the authoritative source for current verbs and behavior.
3. Infer the intended Loom action from the surrounding request instead of requiring a literal verb.
4. If the task is package-manifest specific, also use `.opencode/skills/dotcortex-package-manifests/SKILL.md`.
5. Prefer `loom` verbs when available; otherwise fall back to the matching `make` target or helper script.
6. Report the exact verb used and any tangle or apply step that followed.

## Rules

- Do not edit tangled output directly.
- Do not edit `Makefile`; update `loom.org` instead.
- Re-check `loom.org` or `loom list` when verb availability matters.
- Treat `/loom` as a prefix-style intent marker, not a mandatory standalone command flow.
- Do not force the user to spell the exact verb when the requested outcome already implies it.
- Keep this command doc light; put durable Loom knowledge in the skill file.
