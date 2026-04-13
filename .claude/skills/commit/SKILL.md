---
name: commit
description: /commit — Structured Git Commit
---

# /commit — Structured Git Commit

You are creating a well-structured git commit. The user may provide a hint: $ARGUMENTS

## Steps

1. Run `git status` (never `-uall`) and `git diff --staged` + `git diff` to understand all changes.

2. **Classify the change type:**
   - `feat` — new feature or capability
   - `fix` — bug fix
   - `refactor` — restructuring without behavior change
   - `docs` — documentation only
   - `chore` — maintenance, config, dependencies
   - `tangle` — org source block changes that affect tangled output

3. **Determine scope from file paths:**
   - `emacs` — emacs.org, Spacemacs config
   - `shell` — shell.org, bash/zsh config
   - `flatpak` — flatpak.org, Flatpak management
   - `loom` — loom.org, Makefile, control plane
   - `style` — style.org, LainCore theme
   - `tools` — tools.org, misc tooling
   - `stow` — overlay dirs, stow config
   - `pkg` — package manifests (pip, npm, cargo, guix, etc.)
   - Use the most specific scope that fits

4. **Build the commit message:**
   ```
   TYPE(SCOPE): one-line summary (imperative mood, <72 chars)

   - bullet point details of what changed
   - focus on WHY not just WHAT

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   ```

5. **Stage specific files** — NEVER use `git add .` or `git add -A`. Add files by name. If unsure which files belong, ask.

6. **Commit** using a HEREDOC for the message to preserve formatting.

7. Show `git log -1` to confirm.

## Rules

- If there are no changes, say so and stop.
- If changes span multiple unrelated scopes, suggest splitting into multiple commits.
- If the user's hint conflicts with what the diff shows, trust the diff.
- Do not push unless explicitly asked.
- Remember: `.org` files are the source of truth, tangled output files are generated.
