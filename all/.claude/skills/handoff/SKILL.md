---
name: handoff
description: Session Handoff
---

# Session Handoff

Use this when you need a concise handoff for another session.

## Steps

1. Summarize what changed.
2. Note what was verified.
3. Call out open questions or risks.
4. Keep it short enough to read quickly in a fresh window.

## Rules

- Do not pad with unnecessary context.
- Include only the evidence that matters for continuation.
- A handoff is a session artifact, not DotCortex source. Never create or commit
  `HANDOFF*.md` at the DotCortex repo root or inside a generated overlay.
- Store durable HelmCortex handoffs under
  `~/HelmCortex/LOGS/handoffs/YYYY-MM-DD-<slug>.md`, exactly as required by
  the HelmCortex handoff skill. Verify the destination exists before writing,
  and keep `LOGS/` outside the executor's allowed paths unless the explicit
  task is to archive the handoff.
- Include the source repository, session/date, verification state, and open
  risks in the archived handoff so it remains useful after the source session
  disappears.
