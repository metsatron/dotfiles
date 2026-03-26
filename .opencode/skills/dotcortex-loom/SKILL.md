---
name: dotcortex-loom
description: Operate the DotCortex literate dotfiles system - tangle org files, stow overlays safely, run loom verbs for package management, and handle bootstrap workflows.
---

# DotCortex Loom Operations for OpenCode

Use this skill when working on DotCortex configs, package manifests, tangling, stowing, Loom verbs, or machine bootstrap tasks.

## Path Resolution

Assume the repo root is `~/DotCortex`.

## Trigger Conditions

- User asks to edit a dotfile managed by DotCortex
- User mentions Loom, stow, tangle, overlays, manifests, or bootstrap
- User uses `/loom` as a prefix or asks to do something "with loom"
- User wants package changes through pip, npm, Guix, Flatpak, Snap, Cargo, AppImage, Homebrew, or app manifests
- User asks how DotCortex is structured

## Critical Safety Rules

1. Never touch any `.claude` path or `CLAUDE.md` unless the user explicitly names that exact path for direct modification.
2. Never edit files in overlay output directories directly.
3. Edit the owning root `.org` file instead.
4. Never edit `Makefile` directly; edit `loom.org`.
5. Prefer `make safe-stow` to plain `stow`.
6. Verify with fresh command output before claiming success.
7. If the task likely spans 3 or more files or changes control-plane behavior, plan first.

## Core Commands

```bash
cd ~/DotCortex

# Regenerate overlay output
make tangle

# Preview stow effects
make preview-stow

# Safely stow current machine overlays
make safe-stow
```

## Loom Verbs

Loom depends on Guix's `guile`. If Loom is unavailable, use the matching `make` targets or helper scripts.

`loom.org` is the canonical source for verb coverage. This skill mirrors it for fast routing, but when the repo changes, re-check `loom.org`, `loom`, or `loom list` and trust that live output over this mirror.

```bash
loom
loom list

loom all

loom stow
loom stow:linux
loom stow:debian

loom stow:x230
loom stow:t480s
loom stow:devuan
loom stow:health

loom health
loom desktop:heal
loom swap:heal
loom swap:heal!

loom pip:apply
loom pip:diff
loom pip:capture
loom pip:health

loom npm:apply
loom npm:sync
loom npm:diff
loom npm:capture
loom npm:health

loom guix:apply
loom guix:pull
loom guix:git-bench
loom guix:git-apply
loom guix:dirs
loom guix:gc
loom guix:sub-bench
loom guix:sub-apply
loom guix:pull-root
loom guix:root
loom guix:gc-root

loom flatpak:apply
loom flatpak:diff
loom flatpak:bridge
loom flatpak:x11
loom flatpak:remotes
loom flatpak:release-diff
loom flatpak:perms-capture
loom flatpak:perms-apply

loom nala:repos
loom nala:capture
loom nala:diff
loom nala:release-diff
loom nala:apply
loom nala:health

loom snap:apply
loom snap:sync
loom snap:apply!
loom snap:diff
loom snap:prune
loom snap:autoremove
loom snap:orphans
loom snap:connections
loom snap:capture

loom cargo:apply
loom cargo:sync
loom cargo:diff
loom cargo:capture
loom cargo:health

loom appimage:update
loom appimage:integrate
loom appimage:ail-scrub
loom appimage:health
loom appimage:inventory

loom brew:apply
loom brew:health

loom app:apply
loom app:health

loom bun:apply
loom bun:sync
loom bun:diff
loom bun:capture
loom bun:health

loom bunx:apply
loom bunx:sync
loom bunx:diff
loom bunx:capture
loom bunx:health

loom which-nvim
loom which-zsh

loom root:sync
loom root:config
loom root:earlyoom-dryrun
loom root:which-nvim
```

## Ownership Lookup

To find which org file owns a generated target:

```bash
cd ~/DotCortex
grep -rn "tangle.*path/to/config" *.org
```

Common mappings:

- `~/.bashrc` -> `shell.org`
- `~/.zshrc` -> `shell.org`
- `~/.config/maak/maak.scm` -> `loom.org`
- `Makefile` -> `loom.org`
- Guix manifests -> `guix.org`
- GTK and terminal theme settings -> `style.org`

## Bootstrap Notes

```bash
cd ~/DotCortex && bash INSTALL.sh
```

Important:

- First tangle may require empty `.mk` stubs under `all/.mk/`
- First stow on a fresh machine should use `make safe-stow`, not Loom
- Guix tools may only be visible at `~/.guix-extra-profiles/core/core/bin/`

## Operating Notes

- Root `.org` files are the single source of truth
- Overlay priority is layered from shared to machine-specific
- `safe-stow` creates timestamped backups before replacing real files
- HelmCortex is separate; do not treat it as a DotCortex stow target
- `/loom` is a Loom-first routing convention, not a fixed procedure; infer the intended verb from the surrounding request
- Re-check `loom.org` before updating this skill so the verb list stays current
- Claude-facing materials may be read for reference, but OpenCode changes must land in DotCortex or `.opencode` targets only
