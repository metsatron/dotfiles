---
name: tangle
description: Tangle Org files (like the current skills.org) into their final destinations (e.g., all/.agents/skills/).
model: claude-haiku-4-5-20251001
---

# Tangle Org Sources

Use this when you need to tangle Org files to their destination. This is used by Hermes to update config files.

## Use This Skill For

- Tangling individual Org files (e.g., `tangle-one skills.org`)
- Performing a full `make tangle` across all Org files

## Canonical Commands

- Single file tangle: `tangle-one <file.org>`
- Full tangle: `make tangle`

## Notes

- =tangle-one= lives at =~/DotCortex/all/.local/bin/tangle-one=.
- The Makefile is tangled from =loom.org=.
- Always ensure you are in the =~/DotCortex/= directory before tangling.
