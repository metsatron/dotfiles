---
name: dotcortex-package-manifests
description: Manage DotCortex package manifests from root Org sources.
model: claude-haiku-4-5-20251001
---

# DotCortex Package Manifest Operations

Use this for package-manifest edits in DotCortex: pip, npm, guix, flatpak, snap, cargo, appimage, homebrew, and app manifests.

## Rules

- Edit the owning root Org file.
- Re-tangle before applying.
- Prefer manager-specific Loom verbs when available.
- Do not invent a new manifest layout for an existing manager.
