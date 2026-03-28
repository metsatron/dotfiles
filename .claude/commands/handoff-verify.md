# /handoff-verify — Fresh-Context Verification

Verify completed work with evidence-based checks before reporting done. Run this after implementation, before `/commit` or `/handoff`.

## Steps

1. **Summarize intent** — state what was changed and why in 2-3 lines.

2. **Identify verification commands** — pick the commands that actually prove success for this change. Common DotCortex checks:
   - `make tangle` — org sources tangle without error
   - `make preview-stow` — stow dry-run shows no conflicts
   - `git diff --stat` — changed files match intent (no stray edits)
   - `grep -rn 'PATTERN' *.org` — confirm org source contains the expected content
   - Package scripts: `~/.local/bin/<pkg>-health`, `<pkg>-diff`
   - Loom verbs: `loom <verb>` if the change affects loom

3. **Run them fresh** — execute each command and read the full output. Do not skip or summarize away failures.

4. **Check DotCortex invariants:**
   - Only `.org` source files were edited (not tangled output in overlay dirs)
   - If the Makefile changed, it was via `loom.org` not direct edit
   - New tangled files land in the correct overlay (`all/`, `linux/`, `debian/`, `devuan/`, `x230/`, `t480s/`)
   - SSV manifests use the correct format (`PKG VERSION EXTRA` with `""` for empty fields)

5. **Report only what evidence proves.** Structure:

   ```
   ## Verified
   - [what passed, with command + key output line]

   ## Not Verified
   - [what could not be checked and why]

   ## Issues Found
   - [any failures, with actual error output]
   ```

## Rules

- No completion claims without fresh verification evidence
- "Should work" is not verification — run the command
- Passing one gate does not prove the others
- If no reliable verification command exists, say so plainly and suggest the best manual check
- If verification fails, report the failure state first and fix from there
- Keep the report concise — evidence lines, not prose
