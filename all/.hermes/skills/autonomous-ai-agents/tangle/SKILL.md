---
name: tangle
description: Tangle org files to generate code and SKILL.md files from DotCortex sources.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
 hermes:
 model_primary: claude-haiku-4-5-20251001
 tags: [DotCortex, Tangle, Org-Mode, Code-Generation]
 related_skills: [loom]
 required_commands: [tangle-one, make]
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
