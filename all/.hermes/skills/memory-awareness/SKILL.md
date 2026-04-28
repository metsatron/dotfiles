---
name: memory-awareness
description: Route memory, soul, user-model, TODO, and durable lessons into the right HelmCortex channels.
---

*description: Route memory, soul, user-model, TODO, and durable lessons into the right HelmCortex channels.*

> **Model:** `gpt-5.4` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# Memory Awareness

Use this skill when a task involves memory, `/reflect`, `MEMORY.md`, `USER.md`, `SOUL.md`, identity continuity, durable lessons, or agent-cache consolidation.

## Source Of Truth

- Harness context templates: `FORGE/harness/{scope}/MEMORYS.md`, `SOULS.md`, and `USERS.md`
- Compiler: `FORGE/bin/helmcortex-compile --type context --scope {scope}`
- Compiled outputs: `.{agent}/MEMORY.md`, `.{agent}/SOUL.md`, and `.{agent}/USER.md`
- Local agent notes survive recompilation only inside `<!-- BEGIN LOCAL AGENT NOTES -->` blocks.

## Routing Rules

- If it is a repeatable procedure, update or create a skill.
- If it is an in-flight task or visibility item, update `LOGS/TODO/HelmCortex.md` or `LOGS/TODO/Machines/{hostname}.md`.
- If it is a durable cross-agent fact, put it in the narrowest harness `MEMORYS.md`.
- If it is identity/provenance, put it in the narrowest harness `SOULS.md` as a pointer unless full context must load.
- If it is about Mètsàtron's stable preferences or collaboration model, put it in `USERS.md`.
- If it is canonical doctrine, surface the CORTEX target before writing.

## Known Memory Caches

- `.claude/MEMORY.md` and `.claude/USER.md`
- `.codex/MEMORY.md` and `.codex/USER.md`
- `.agents/MEMORY.md` and `.agents/USER.md`
- `.opencode/MEMORY.md` and `.opencode/USER.md`
- `.hermes/memories/MEMORY.md` and `.hermes/memories/USER.md`
- `FORGE/brain/auryn/`
- `FORGE/brain/helmastra/`

## Workflow

1. Identify whether the lesson is local cache, shared memory, user model, soul/provenance, TODO, skill, or CORTEX.
2. Write it to the narrowest source of truth, not merely the currently loaded generated file.
3. If a generated context file must receive an agent-local note, write only inside the local notes block.
4. Recompile with `helmcortex-compile --type context --scope {scope}` after harness template edits.
5. Report where the memory was persisted so future agents do not have to rediscover it.

## Soul Pointers

- Auryn quarters: `FORGE/brain/auryn/`
- HelmAstra quarters: `FORGE/brain/helmastra/`
- HelmAstra authored soul: `FORGE/brain/helmastra/SOUL.md`
- HelmAstra authored name card: `FORGE/brain/helmastra/HELMASTRA.md`
- HelmAstra compiled runtime law: `FORGE/brain/helmastra/AGENTS.md`

