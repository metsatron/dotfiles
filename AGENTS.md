# DotCortex — Agent Instructions

## What This Is

DotCortex is a literate, declarative, reproducible dotfiles system. Org-mode files at the repo root are the single source of truth. They tangle into overlay directories which GNU Stow symlinks into `$HOME`.

See `CLAUDE.md` for full architecture details, common workflows, and package manifest reference.

## Critical Rules

1. **Never edit tangled output** — files inside `all/`, `linux/`, `debian/`, `think/`, `be/`, `navi/`, `arch/`, `osx/` are generated. Edit the `.org` source at repo root instead.
2. **Org files are canonical** — every config, script, and manifest is defined inside an org code block with a `:tangle` target.
3. **Stow target is `$HOME`** — the repo lives at `~/DotCortex`.
4. **Use `make safe-stow`** — it backs up existing files before stowing. Never use plain `stow` directly.
5. **Follow existing patterns** — new package managers get: `.org` file + SSV manifest + capture/diff/apply/health scripts + `.mk` Makefile fragment + loom verbs.

## Build & Apply

```bash
cd ~/DotCortex
make tangle                                          # org → overlay files
make safe-stow STOW_PKGS="all linux debian think"   # stow with backup
```

## Package Manifests

| Manager  | Org File       | Loom Verbs                     |
|----------|----------------|--------------------------------|
| Pip      | `pip.org`      | `pip:apply`, `pip:diff`        |
| NPM      | `npm.org`      | `npm:apply`, `npm:diff`        |
| Guix     | `guix.org`     | `guix:apply`, `guix:pull`      |
| Flatpak  | `flatpak.org`  | `flatpak:apply`, `flatpak:diff`|
| Snap     | `snap.org`     | `snap:apply`, `snap:diff`      |
| Cargo    | `cargo.org`    | `cargo:apply`, `cargo:diff`    |
| AppImage | `appimage.org` | `appimage:update`              |
| Homebrew | `homebrew.org` | `brew:apply`                   |

## Finding What Owns a Config

```bash
grep -rn "tangle.*path/to/config" *.org
```

## Bootstrap

```bash
cd ~/DotCortex && bash INSTALL.sh
```

## HelmCortex

DotCortex coexists with HelmCortex (knowledge/project system) at `~/HelmCortex`. Shell PATH entries include `$HOME/HelmCortex/FORGE/bin` for tools like `auryn` (brain CLI).
