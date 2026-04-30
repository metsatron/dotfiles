---
name: handoff
description: Session Handoff
model: claude-sonnet-4-6
---

# Session Handoff

Use this when you need a concise handoff for another session.

## Steps

1. Summarize what changed.
2. Note what was verified.
3. Call out open questions or risks.
4. Keep it short enough to read quickly in a fresh window.
5. Write the handoff document to `LOGS/handoffs/YYYY-MM-DD-<slug>.md` — use today's date and a 3-5 word kebab-case slug describing the session topic.
6. Append a wiki link to the handoff in `LOGS/TODO/HelmCortex.md` under the Active section:
   `- [ ] **RESUME YYYY-MM-DD** <topic> — see handoff: [[LOGS/handoffs/YYYY-MM-DD-<slug>]]`

## Rules

- Do not pad with unnecessary context.
- Include only the evidence that matters for continuation.
- Handoff files live ONLY in `LOGS/handoffs/` — never in session export dirs (`LOGS/Claude/`, `LOGS/Codex/`, etc.) or anywhere else.
- The TODO wiki link must use the Obsidian double-bracket format and omit the `.md` extension.
