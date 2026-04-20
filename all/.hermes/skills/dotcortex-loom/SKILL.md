---
name: dotcortex-loom
description: Operate the DotCortex literate dotfiles system — tangle org files, stow overlays, run loom verbs for package management (pip, npm, guix, flatpak, snap, cargo, appimage, homebrew), and bootstrap fresh machines.
model: claude-haiku-4-5-20251001
---

# DotCortex Loom Operations

Use this skill when the task involves DotCortex configuration, dotfiles management, package manifests, loom verbs, or system provisioning.

## Path Resolution

DotCortex lives at `~/DotCortex`. All commands assume this as the working directory unless stated otherwise.

## Core Build Commands

```bash
cd ~/DotCortex

# Tangle all org files into overlay directories
make tangle

# Tangle a single org file (faster, preferred for focused changes)
tangle-one shell.org

# Preview what stow would do (dry-run)
make preview-stow

# Stow with loom (normal workflow, requires Guix)
loom stow:x230          # X230: all linux debian x230
loom stow:t480s         # T480s: all linux debian devuan t480s
loom stow:devuan        # shared: all linux devuan

# Without loom (bootstrap or no Guix)
STOW_PKGS='all linux debian devuan t480s' make safe-stow

# Full rebuild
make tangle && loom stow:t480s
```

## Loom Verbs (Guile Control Plane)

Loom requires Guix guile. Without guile, use make targets or scripts directly.

```bash
# List all available verbs
loom

# Package management
loom pip:apply          # Install pip packages from manifest
loom pip:diff           # Show manifest vs installed diff
loom pip:capture        # Capture current pip state to manifest
loom pip:health         # Show Python/pip environment

loom npm:apply          # Enforce npm manifest (install + uninstall extras)
loom npm:sync           # Install only, no removals
loom npm:diff           # Show manifest vs installed diff
loom npm:capture        # Capture current npm state to manifest
loom npm:health         # Show Node/npm environment

loom guix:apply         # Apply Guix manifests to profiles
loom guix:pull          # Pull Guix channel updates

loom flatpak:apply      # Apply Flatpak manifest
loom flatpak:diff       # Show manifest vs installed diff
loom flatpak:bridge     # Bridge fonts/themes into Flatpak sandboxes

loom nala:apply         # Enforce nala/apt manifest (install missing)
loom nala:diff          # Show manifest vs installed diff
loom nala:capture       # Capture live apt packages to manifest
loom nala:repos         # Ensure third-party apt repos configured
loom nala:health        # Show nala/apt/dpkg status

loom snap:apply         # Apply Snap manifest
loom snap:diff          # Show manifest vs installed diff

loom cargo:apply        # Apply Cargo manifest
loom cargo:diff         # Show manifest vs installed diff

loom appimage:update    # Update all AppImages

loom stow               # Stow all overlays
loom stow:health        # Check symlink health
```

## Editing Configs

CRITICAL: Never edit files inside `all/`, `linux/`, `debian/`, `devuan/`, `x230/`, `t480s/`, etc. directly. These are tangled output. Edit the `.org` source file instead.

To find which org file owns a config:

```bash
cd ~/DotCortex
grep -rn "tangle.*path/to/config" *.org
```

Common mappings:
- `~/.bashrc` / `~/.zshrc` -> `shell.org`
- `~/.config/maak/maak.scm` -> `loom.org`
- `Makefile` -> `loom.org` (the Makefile template block)
- GTK/terminal themes -> `style.org`
- Guix manifests -> `guix.org`

## Package Manifest Format

All manifests use SSV (space-separated values):

```
# PKG VERSION EXTRA
litellm "" ""
openai "" ""
```

## Adding a New Package to a Manifest

1. Edit the org file (e.g., `pip.org`)
2. Add a row to the manifest `#+BEGIN_SRC text` block
3. Run `tangle-one pip.org` to regenerate the SSV file
4. Run the apply verb: `loom pip:apply`

Or use the capture verb to auto-detect what is installed:

```bash
loom pip:capture    # Appends any new packages to manifest
loom npm:capture
```

## Operating Notes

- Org files at repo root are the single source of truth
- `make safe-stow` creates timestamped backups before overwriting
- Overlays stack in priority order: `all` -> `linux` -> `debian` -> `devuan`/`x230`/`t480s` (later wins)
- The Makefile includes fragment `.mk` files from `all/.mk/`
- Loom runs via Guix's guile — without Guix, use make targets directly
