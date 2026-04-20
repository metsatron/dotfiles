---
name: loom
description: Operate DotCortex with loom verbs (e.g., pip:apply, npm:sync, guix:apply, or stow verbs) via full explicit paths for Hermes workflow.
model: claude-haiku-4-5-20251001
---

# Loom Verbs for DotCortex Operations

Use this skill when you need to operate DotCortex with loom verbs (e.g., pip:apply, npm:sync, guix:apply, or stow verbs) via full explicit paths for Hermes workflow.

## Use This Skill For

- Applying package manifests (pip, npm, guix, flatpak, snap, cargo, appimage, homebrew)
- Performing stow operations (e.g., `loom stow:x230`)
- Capturing package states to manifests
- Checking health of package environments

## Canonical Commands (Explicit Paths for Hermes)

- pip: `~/DotCortex/all/.local/bin/loom pip:apply`
- npm: `~/DotCortex/all/.local/bin/loom npm:sync`
- guix: `~/DotCortex/all/.local/bin/loom guix:apply`
- stow: `~/DotCortex/all/.local/bin/loom stow:x230` (replace `x230` with target machine)

## Notes

- The `loom` executable itself is part of the Guix profile and needs to be in the PATH.
- `~/DotCortex/all/.local/bin/loom` is a wrapper script to ensure the correct environment and `maak.scm` are used.
- Always ensure you are in the `~/DotCortex/` directory before running loom verbs.
