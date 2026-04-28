---
name: pixelcortex-ports
description: Add or update a port entry in PixelCortex — document source, license, build instructions, and RetroPie integration details.
---

*description: Add or update a port entry in PixelCortex — document source, license, build instructions, and RetroPie integration details.*

> **Model:** `gpt-5.4-mini` | **Effort:** `low` | **Delegate:** `mini`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# PixelCortex Ports

Use this skill when documenting a game port under `ports/`.

## Structure

Each port has its own directory: `ports/{port-slug}/` with a `README.md` containing:

- Source repo or upstream URL
- License (GPLv2, GPLv3, commercial, etc.)
- Build dependencies
- RetroPie integration notes
- Configuration files and paths

## Steps

1. Check if the port directory already exists under `ports/`.
2. If not, create `ports/{port-slug}/README.md`.
3. Document source, license, and build instructions.
4. Cross-link from the relevant `systems/` entry if the port replaces or supplements a native ROM.

## Rules

- Port slugs use kebab-case matching the RetroPie port directory name where possible.
- Do not include binary downloads — only source references and build instructions.
- License information is mandatory for every port entry.

## PixelForge Bin Tools

Console-specific conversion utilities in `FORGE/PixelForge/bin/`:

| Tool | Purpose |
|------|---------|
| `convert-to-game-nintendont` | Convert game images for Nintendont (Wii GameCube loader) |
| `convert-to-game-usbloadergx` | Convert game images for USB Loader GX (Wii) |
| `ps3-merge` | Merge split PS3 ISOs |
| `ps3-split-iso` / `ps3-split-pkg` | Split PS3 ISOs/PKGs for FAT32 transport |

Reference these when documenting port setup steps that involve image conversion.

