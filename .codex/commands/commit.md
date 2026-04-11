---
name: commit
description: commit - Structured DotCortex Commit
---

# commit - Structured DotCortex Commit

Use this when the user explicitly asks for a DotCortex commit.

## Steps

1. Inspect `git status`, `git diff --staged`, and `git diff`
2. Classify the change:
   - `feat`
   - `fix`
   - `refactor`
   - `docs`
   - `chore`
   - `script`
3. Pick a useful scope from the files changed, such as:
   - `flatpak`
   - `loom`
   - `bootstrap`
   - `shell`
   - `style`
   - `opencode`
4. Build a concise commit message in imperative mood
5. Verify the change with the smallest relevant fresh command set before committing
6. Stage files by name only, never `git add .` or `git add -A`
7. Commit and verify with `git log -1 --stat`

## Rules

- Do not commit unrelated user changes
- If both org sources and tangled outputs belong together, stage both when appropriate
- Prefer commit messages that explain why the change exists, not just what changed
- Keep the staged diff surgical; do not slip in adjacent cleanup
- Do not push unless explicitly asked
