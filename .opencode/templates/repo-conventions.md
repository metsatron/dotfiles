# Repo Conventions Template

Use this as a quick OpenCode checklist before making changes in DotCortex.

## Source of Truth

- Prefer root-level `.org` files as the editable source
- Treat overlay directories as generated output
- Treat `Makefile` as generated from `loom.org`

## Safe Editing Rules

- Search ownership before editing generated configs
- Avoid editing machine overlays directly unless the user explicitly asks for generated-output inspection only
- Preserve unrelated user changes in a dirty worktree
- Never write to any `.claude` path or `CLAUDE.md` unless the user explicitly names that exact path for direct modification
- Do not remove Claude-specific materials while adding OpenCode materials
- Prefer surgical edits over opportunistic cleanup
- Convert external agent ideas into `.opencode` docs instead of copying client-specific machinery

## Validation Defaults

- Run `make tangle` after changing org sources
- Use `make preview-stow` when a change affects stowed files
- Use `make safe-stow` when applying local config changes
- Prefer lightweight verification over destructive operations
- Do not claim success without fresh verification evidence from the current session
- If the task likely spans 3 or more files or changes repo control-plane behavior, plan first

## Repo-Specific Cues

- Check Guix profile bins before assuming a tool is missing
- Keep HelmCortex boundaries intact
- Follow existing package-manager patterns instead of inventing new shapes
