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
- User wants package changes through pip, npm, Guix, Flatpak, Snap, Cargo, AppImage, Homebrew, or app manifests
- User asks how DotCortex is structured

## Critical Safety Rules

1. Never edit files in overlay output directories directly.
2. Edit the owning root `.org` file instead.
3. Never edit `Makefile` directly; edit `loom.org`.
4. Prefer `make safe-stow` to plain `stow`.

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

```bash
loom

loom stow:x230
loom stow:t480s
loom stow:devuan

loom pip:apply
loom pip:diff
loom pip:health

loom npm:apply
loom npm:diff
loom npm:health

loom guix:apply
loom guix:pull

loom flatpak:apply
loom flatpak:diff

loom snap:apply
loom snap:diff

loom cargo:apply
loom cargo:diff

loom appimage:update
loom brew:apply
loom app:apply
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
