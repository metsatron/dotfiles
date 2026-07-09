---
name: reflect
description: Session Reflection
model: claude-sonnet-5
---

# Session Reflection

Use this when a session has enough durable discoveries to justify a short reflection.

**A reflection that ends in the transcript is worthless.** The purpose of this skill is to move a lesson out of volatile context and into a file that governs future sessions. If you finish without writing to disk, you have not reflected — you have only narrated. Do not ask permission to persist; persisting IS the skill. Ask only when the correct target is genuinely ambiguous.

## Steps

1. Identify what was learned, and separate durable knowledge from one-off implementation detail.
2. For each durable lesson, choose the **narrowest source of truth that still prevents recurrence** (see Targets). A universal lesson filed only in a project file is half a fix; a project quirk filed globally is noise in every session.
3. Establish a reversal point before editing: if the target `.org` has unstaged changes, `git add` that exact path first.
4. Edit the `.org` source — **never the tangled output** — then `tangle-one <file>.org`.
5. Verify the emitted file actually changed: `git status --short`, and grep the emitted file for your text.
6. Report what you wrote and where, in one or two lines.

## Targets

| Lesson type | Source of truth | Emits to |
|---|---|---|
| Universal agent behaviour (any repo) | `agents.org`, global block | `all/.claude/CLAUDE.md` → `~/.claude/CLAUDE.md` |
| Agent behaviour scoped to this repo | `agents.org`, `dotcortex-shared` block | `AGENTS.md` + `CLAUDE.md` |
| Tool or environment gotcha | matching gotchas skill in `skills.org` (`dotcortex-gotchas`, `sanctuary-gotchas`, `pi-agent-gotchas`) | `all/.claude/skills/...` |
| A fact about one specific config | a comment in the owning `.org` block | that config's tangled file |
| Outstanding task or follow-up | `~/HelmCortex/LOGS/TODO/{workspace}.md`, or `Machines/{hostname}.md` if machine-specific | — |

## Rules

- Keep each lesson short and imperative. State the trap and the counter-move, not the story of discovering it.
- Prefer durable notes over transcript-style summaries. Nobody rereads a narrative.
- Never edit an emitted or tangled file directly. The `.org` source is canonical.
- If a lesson is worth a rule, write it as a rule — numbered, named, and stating the failure mode it prevents.
- If nothing durable emerged, say so in one line and write nothing. A forced reflection is worse than none.
