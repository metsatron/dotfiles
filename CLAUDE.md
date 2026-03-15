# DotCortex — Literate Dotfiles System

## What This Is

DotCortex is Mètsàtron's declarative, literate, reproducible dotfiles system. Org-mode files are the single source of truth. They tangle into overlay directories (`all/`, `linux/`, `debian/`, `think/`) which GNU Stow symlinks into `$HOME`.

## Architecture

```
*.org files  →  make tangle  →  overlay dirs  →  make safe-stow  →  $HOME
```

- **Org files** (root level): canonical source for all configs, scripts, manifests
- **Overlay dirs**: `all/` (shared), `linux/`, `debian/`, `arch/`, `osx/`, `think/` (hardware), `be/`, `navi/`
- **Stow**: symlinks overlay contents into `$HOME`, stacked in priority order
- **Loom**: Guile Scheme control plane (`~/.local/bin/loom`) with 50+ task verbs

## Critical Rules

1. **Never edit tangled output files** — edit the `.org` source and re-tangle
2. **Org files are at repo root** — the overlay dirs contain only tangled output
3. **Stow target is `$HOME`** — the repo must live at `~/DotCortex`
4. **`make safe-stow`** backs up existing files before stowing — use it instead of `make stow`

## Common Workflows

```bash
# Full rebuild
cd ~/DotCortex && make tangle && make safe-stow STOW_PKGS="all linux debian think"

# Edit a config
# 1. Find the org source: grep for the config path in *.org
# 2. Edit the org block
# 3. make tangle && make safe-stow

# Loom verbs (requires Guix guile)
loom                    # list all verbs
loom guix:apply         # apply Guix manifest
loom flatpak:apply      # apply Flatpak manifest
loom pip:apply          # install pip manifest
loom npm:apply          # install npm manifest
loom stow               # stow all overlays
```

## Package Manifests

Each package manager has an `.org` file that tangles a manifest (`.ssv`) and helper scripts:

| Manager  | Org File       | Manifest                              | Loom Verbs                        |
|----------|----------------|---------------------------------------|-----------------------------------|
| Guix     | `guix.org`     | `.config/guix/manifests/*.scm`        | `guix:apply`, `guix:pull`         |
| Flatpak  | `flatpak.org`  | `linux/.flatpak/manifest/apps.ssv`    | `flatpak:apply`, `flatpak:diff`   |
| Snap     | `snap.org`     | `all/.snap/manifest/apps.ssv`         | `snap:apply`, `snap:diff`         |
| Pip      | `pip.org`      | `all/.pip/manifest/packages.ssv`      | `pip:apply`, `pip:diff`           |
| NPM      | `npm.org`      | `all/.npm/manifest/global.ssv`        | `npm:apply`, `npm:diff`           |
| Cargo    | `cargo.org`    | `all/.cargo/manifest/crates.ssv`      | `cargo:apply`, `cargo:diff`       |
| AppImage | `appimage.org` | `all/.appimage/inventory/all.ssv`     | `appimage:update`                 |
| Homebrew | `homebrew.org` | `all/.homebrew/manifest/brews.ssv`    | `brew:apply`                      |
| Apps     | `app.org`      | `all/.app/manifest/apps.ssv`          | `app:apply`                       |

## Key Files

- `Makefile` — build system entry point (tangle, stow, guix-dirs)
- `loom.org` — control plane, Makefile template, batch helpers
- `shell.org` — bash/zsh rc, exports, aliases, functions, prompt
- `style.org` — LainCore theme (fonts, colours, GTK, terminal, Emacs)
- `INSTALL.sh` — bootstrap script for fresh machines
- `README.org` — full documentation

## HelmCortex Integration

DotCortex coexists with HelmCortex (the knowledge/project system). HelmCortex lives at `~/HelmCortex` (may be a symlink to a mount). DotCortex manages shell PATH entries that include `$HOME/HelmCortex/FORGE/bin` for tools like `auryn`.

## When Working on DotCortex

- Use `@dotcortex-loom` skill for loom verb operations
- Always edit `.org` source, never tangled output
- Test with `make tangle` before stowing
- Use `make preview-stow` to dry-run before applying
