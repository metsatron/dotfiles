# Source Map

This directory was built from the current Claude-facing repo guidance.

Those source files were treated as read-only reference material.

Primary inputs:

- `AGENTS.md` - repo-safe editing rules, stow guidance, overlay rules, machine layout
- `CLAUDE.md` - architecture, workflows, gotchas, package manager patterns, HelmCortex notes
- `README.org` - broader grimoire documentation, bootstrap flow, target behavior, structure notes
- `.claude/skills/dotcortex-loom/SKILL.md` - task-oriented operational skill for Loom and DotCortex

Replication approach:

- Preserve all existing Claude files unchanged
- Add OpenCode-local references under `.opencode/`
- Mirror the DotCortex Loom skill with current repo naming and safer defaults
- Condense repeated repo knowledge into one working reference for future OpenCode sessions
