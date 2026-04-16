---
name: antigravity-config
description: Manage Antigravity from DotCortex source files.
model: claude-sonnet-4-6
---

# Antigravity Configuration

Use this when Antigravity should be configured through DotCortex source files.

## Use This Skill For

- finding the owning Org file for an Antigravity config change
- editing the canonical DotCortex source instead of generated output
- tangling and verifying the resulting Antigravity configuration

## Rules

- Keep package metadata in `nala.org`.
- Keep user config tangles in the repo root Org files.
- Verify the generated output after tangling.
- Prefer the established package/source mapping.
