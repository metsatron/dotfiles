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
8. Use `.opencode/commands/skill-sync.md` when the local OpenCode layer needs to catch up with `.claude/`, `.agents/`, or `.codex/`.
9. Use `.opencode/commands/todo.md` when routing or reviewing task items across DotCortex tracking files.

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
- VoxForge `pvox` is the speaking layer; long-form speech defaults to Amy Medium and short attention cues can use `ClaudeMX`
- `pclip default` on `Meta+V` is the preferred user-driven way to hear selected assistant output aloud
- When speech is requested, prefer `pvox say Claude --stdin`; when fast playback matters, prefer `pvox say Claude --stdin --stream` with `PVOX_PLAYER_RAW=aplay`
- On major task completion, alert by default with `ClaudeMX: "Meu Comandante!"` followed by `Claude: "Check OpenCode!"` unless the user asks for silence
- Antigravity belongs to DotCortex's `nala.org` layer, including install/repo metadata and user config tangles

## OpenCode Memory

- `.opencode/memory/README.md`
- `.opencode/memory/user-metsatron.md`
- `.opencode/memory/task-tracking.md`
- `.opencode/memory/wezterm-host-sendtext.md`
- `.opencode/memory/helmcortex-context.md`
- `.opencode/memory/pvox-workflow.md`
- `.opencode/memory/antigravity.md`

## Canonical Sources

- `AGENTS.md`
- `CLAUDE.md`
- `README.org`
- `.claude/skills/dotcortex-loom/SKILL.md`
- `.opencode/skills/antigravity-config/SKILL.md`

If this file and a canonical source diverge, trust the canonical source.
