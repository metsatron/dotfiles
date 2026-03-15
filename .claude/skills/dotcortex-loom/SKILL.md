---
name: dotcortex-loom
description: Operate the DotCortex literate dotfiles system — tangle org files, stow overlays, run loom verbs for package management (pip, npm, guix, flatpak, snap, cargo, appimage, homebrew), and bootstrap fresh machines.
---

# DotCortex Loom Operations

Use this skill when the task involves DotCortex configuration, dotfiles management, package manifests, loom verbs, or system provisioning.

## Path Resolution

DotCortex lives at `~/DotCortex`. All commands assume this as the working directory unless stated otherwise.

## Trigger Conditions

- User asks to install/manage packages via loom
- User wants to edit a dotfile, shell config, or system service
- User mentions tangle, stow, loom, or overlay
- User wants to set up a new machine or bootstrap
- User asks about DotCortex architecture

## Core Build Commands

```bash
cd ~/DotCortex

# Tangle all org files into overlay directories
make tangle

# Preview what stow would do (dry-run)
make preview-stow

# Safely stow with automatic backups of conflicts
make safe-stow STOW_PKGS="all linux debian think"

# Full rebuild
make tangle && make safe-stow STOW_PKGS="all linux debian think"
```

## Loom Verbs (Guile Control Plane)

Loom requires Guix guile. If guile is not available, use the make targets or scripts directly.

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

loom snap:apply         # Apply Snap manifest
loom snap:diff          # Show manifest vs installed diff

loom cargo:apply        # Apply Cargo manifest
loom cargo:diff         # Show manifest vs installed diff

loom appimage:update    # Update all AppImages

loom stow               # Stow all overlays
loom stow:health        # Check symlink health
```

## Editing Configs

CRITICAL: Never edit files inside `all/`, `linux/`, `debian/`, `think/` etc directly. These are tangled output. Edit the `.org` source file instead.

To find which org file owns a config:

```bash
cd ~/DotCortex
grep -rn "tangle.*path/to/config" *.org
```

Common mappings:
- `~/.bashrc` → `shell.org`
- `~/.zshrc` → `shell.org`
- `~/.bash_exports` → `shell.org`
- `~/.config/maak/maak.scm` → `loom.org`
- `Makefile` → `loom.org` (the Makefile block is in loom.org)
- GTK/terminal themes → `style.org`
- Guix manifests → `guix.org`

## Package Manifest Format

All manifests use SSV (space-separated values) with comment headers:

```
# ~/DotCortex/all/.pip/manifest/packages.ssv
# PKG VERSION EXTRA
litellm "" ""
openai "" ""
```

Empty `""` means "use latest" or "no value".

## Adding a New Package to a Manifest

1. Edit the org file (e.g., `pip.org`)
2. Add a row to the manifest `#+BEGIN_SRC text` block
3. Run `make tangle` to regenerate the SSV file
4. Run the apply verb: `loom pip:apply`

Or use the capture verb to auto-detect what's installed:

```bash
loom pip:capture    # Appends any new packages to manifest
loom npm:capture
```

## Bootstrap (Fresh Machine)

```bash
cd ~/DotCortex && bash INSTALL.sh
```

This installs system deps (git, stow, emacs-nox, python3, nodejs, etc), tangles, stows, installs pip/npm manifests, and optionally installs GNU Guix.

## Operating Notes

- Org files at repo root are the single source of truth
- `make safe-stow` creates timestamped backups before overwriting
- Overlays stack: `all` → `linux` → `debian` → `think` (later wins)
- The Makefile includes fragment `.mk` files from `all/.mk/`
- Loom runs via Guix's guile — without Guix, use make targets directly
