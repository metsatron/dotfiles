---
name: handoff-verify
description: handoff-verify — Fresh-Context Verification
---

---
description: Verify completed work with evidence-based checks before reporting done.
---

# handoff-verify — Fresh-Context Verification

Verify completed DotCortex work with evidence before claiming done. Run after implementation, before commit or handoff.

## Steps

1. Summarize what was changed and why in 2-3 lines.
2. Identify the commands that prove success for this change:
   - `make tangle` — org sources tangle without error
   - `make preview-stow` — stow dry-run shows no conflicts
   - `git diff --stat` — changed files match intent
   - `grep -rn 'PATTERN' *.org` — org source contains expected content
   - Package scripts: `~/.local/bin/<pkg>-health`, `<pkg>-diff`
   - Loom verbs: `loom <verb>` if the change affects loom
3. Run them fresh and read the full output.
4. Check DotCortex invariants:
   - Only `.org` source files were edited (not tangled output)
   - Makefile changes came via `loom.org`
   - New tangled files land in the correct overlay
   - SSV manifests use correct format (`PKG VERSION EXTRA` with `""` for empty)
5. Report what evidence proves:
   - **Verified** — what passed, with command + key output
   - **Not Verified** — what could not be checked and why
   - **Issues Found** — failures with actual error output

## Rules

- No completion claims without fresh verification evidence
- "Should work" is not verification — run the command
- Passing one gate does not prove the others
- If no reliable verification command exists, say so and suggest a manual check
- If verification fails, report the failure first, then fix
