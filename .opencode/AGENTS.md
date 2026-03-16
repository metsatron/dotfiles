# OpenCode - DotCortex Instructions

Use this directory as OpenCode's local mirror of the repo guidance.

## Core Rules

1. Never edit tangled output in `all/`, `linux/`, `debian/`, `devuan/`, `x230/`, `t480s/`, `be/`, `navi/`, `arch/`, or `osx/`.
2. Edit root-level `.org` files, then run `make tangle`.
3. Never edit `Makefile` directly; edit the Makefile block in `loom.org`.
4. Stow into `$HOME` from `~/DotCortex`.
5. Prefer `make safe-stow` over plain `stow`.
6. Loom requires Guix's `guile`; when Loom is unavailable, use `make` targets directly.
7. Check `~/.guix-extra-profiles/core/core/bin/` before assuming tools are missing.

## Working Flow

- Find config ownership with `grep -rn "tangle.*path/to/config" *.org`
- Edit the owning `.org` file
- Run `make tangle`
- Run `make preview-stow` or `make safe-stow`
- Use `loom stow:x230`, `loom stow:t480s`, or `loom stow:devuan` when Loom is available

## Learned Preferences

- Prefer minimal edits that fix exactly one thing at a time
- Re-read the current file state before iterative fixes to avoid stale assumptions
- For DotCortex-managed output, edit the root `.org` source and re-tangle rather than patching generated files directly
- Canonical task tracking lives in HelmCortex Obsidian TODO files, not in repo comments or ad hoc notes
- WezTerm Flatpak panes run on the host; `send_text` echo suppression requires a separate `stty -echo` injection first

## OpenCode Memory

- `.opencode/memory/README.md`
- `.opencode/memory/user-metsatron.md`
- `.opencode/memory/task-tracking.md`
- `.opencode/memory/wezterm-host-sendtext.md`
- `.opencode/memory/helmcortex-context.md`

## Canonical Sources

- `AGENTS.md`
- `CLAUDE.md`
- `README.org`
- `.claude/skills/dotcortex-loom/SKILL.md`

If this file and a canonical source diverge, trust the canonical source.
