# OpenCode - DotCortex Instructions

Use this directory as OpenCode's local mirror of the repo guidance.

## Core Rules

1. Never touch any `.claude` path or `CLAUDE.md` unless the user explicitly names that exact path for direct modification.
2. Never edit tangled output in `all/`, `linux/`, `debian/`, `devuan/`, `x230/`, `t480s/`, `be/`, `navi/`, `arch/`, or `osx/`.
3. Edit root-level `.org` files, then run `make tangle`.
4. Never edit `Makefile` directly; edit the Makefile block in `loom.org`.
5. Stow into `$HOME` from `~/DotCortex`.
6. Prefer `make safe-stow` over plain `stow`.
7. Loom requires Guix's `guile`; when Loom is unavailable, use `make` targets directly.
8. Check `~/.guix-extra-profiles/core/core/bin/` before assuming tools are missing.
9. Use `.opencode/commands/skill-sync.md` when the local OpenCode layer needs to catch up with `.claude/`, `.agents/`, or `.codex/`.
10. Use `.opencode/commands/todo.md` when routing or reviewing task items across DotCortex tracking files.
11. Interpret `/loom` as a Loom-first routing convention, not a fixed procedure; use `.opencode/commands/loom.md` plus the Loom skill, then infer the right verb from the rest of the request.
12. Treat `.claude/settings.local.json` hooks and permissions as read-only source material; adapt only the useful manual workflow, never present Claude hooks as active OpenCode features.

## Build & Apply

```bash
cd ~/DotCortex

# Regenerate overlay output
make tangle

# Preview what stow would do (dry-run)
make preview-stow

# Apply with automatic backups
make safe-stow

# With Loom (requires Guix guile)
loom stow:x230                          # X230: all linux debian x230
loom stow:t480s                         # T480s: all linux debian devuan t480s
loom stow:devuan                        # shared: all linux devuan
```

## Working Flow

- Find config ownership with `grep -rn "tangle.*path/to/config" *.org`
- Edit the owning `.org` file
- Run `make tangle`
- Run `make preview-stow` or `make safe-stow`
- Use `loom stow:x230`, `loom stow:t480s`, or `loom stow:devuan` when Loom is available

## Learned Preferences

- Prefer minimal edits that fix exactly one thing at a time
- Take what works, leave what does not, and rewrite it for OpenCode and DotCortex instead of copying client-specific machinery
- Re-read the current file state before iterative fixes to avoid stale assumptions
- Use subagents for broad exploration, verbose output, or browser-heavy inspection so main context stays focused
- For DotCortex-managed output, edit the root `.org` source and re-tangle rather than patching generated files directly
- Do not claim completion without fresh verification evidence from the current session
- Plan first when a change is likely to span 3 or more files or alters control-plane behavior
- Canonical task tracking lives in HelmCortex Obsidian TODO files, not in repo comments or ad hoc notes
- WezTerm Flatpak panes run on the host; `send_text` echo suppression requires a separate `stty -echo` injection first
- VoxForge `pvox` is the speaking layer; long-form speech defaults to Amy Medium and short attention cues can use `ClaudeMX`
- `pclip default` on `Meta+V` is the preferred user-driven way to hear selected assistant output aloud
- When speech is requested, prefer `pvox say Claude --stdin`; when fast playback matters, prefer `pvox say Claude --stdin --stream` with `PVOX_PLAYER_RAW=aplay`
- On major task completion, alert by default with `ClaudeMX: "Meu Comandante!"` followed by `Claude: "Check OpenCode!"` unless the user asks for silence
- Antigravity belongs to DotCortex's `nala.org` layer, including install/repo metadata and user config tangles

## Package Manifests (Quick Reference)

| Manager  | Org File       | Loom Verbs                      |
|----------|----------------|---------------------------------|
| Pip      | `pip.org`      | `pip:apply`, `pip:diff`         |
| NPM      | `npm.org`      | `npm:apply`, `npm:diff`         |
| Guix     | `guix.org`     | `guix:apply`, `guix:pull`       |
| Flatpak  | `flatpak.org`  | `flatpak:apply`, `flatpak:diff` |
| Snap     | `snap.org`     | `snap:apply`, `snap:diff`       |
| Cargo    | `cargo.org`    | `cargo:apply`, `cargo:diff`     |
| AppImage | `appimage.org` | `appimage:update`               |
| Homebrew | `homebrew.org` | `brew:apply`                    |
| Apps     | `app.org`      | `app:apply`                     |

## OpenCode Memory

- `.opencode/memory/README.md`
- `.opencode/memory/user-metsatron.md`
- `.opencode/memory/task-tracking.md`
- `.opencode/memory/wezterm-host-sendtext.md`
- `.opencode/memory/helmcortex-context.md`
- `.opencode/memory/pvox-workflow.md`
- `.opencode/memory/antigravity.md`

## OpenCode Skills

- `.opencode/skills/context-hygiene/SKILL.md`
- `.opencode/skills/dotcortex-gotchas/SKILL.md`
- `.opencode/skills/dotcortex-multihost/SKILL.md`
- `.opencode/skills/dotcortex-packages/SKILL.md`

## Canonical Sources And Read-Only References

- `AGENTS.md`
- `README.org`
- `.opencode/skills/antigravity-config/SKILL.md`

Read-only reference material when needed:

- `CLAUDE.md`
- `.claude/skills/dotcortex-loom/SKILL.md`

If this file and a canonical source diverge, trust the canonical source.
