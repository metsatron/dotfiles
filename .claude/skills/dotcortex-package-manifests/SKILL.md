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
- **Category-manifest law (Mètsàtron, sealed 2026-07-10): NEVER create a new per-package .org file.** Package installs go in the manager's manifest org (cargo.org, guix.org, ...); package CONFIG goes in the existing category org that owns its domain (terminal tools → term.org, X desktop userland → x11.org, multiplexers → mux.org, theming → style.org, ...). Offenders already absorbed: yazi.org → term.org, rofi.org → x11.org. If no category org fits, ask Mètsàtron — do not mint one per package.
