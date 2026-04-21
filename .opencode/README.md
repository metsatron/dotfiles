# OpenCode Workspace Notes

This directory is OpenCode's local home for DotCortex-specific guidance.

- It does not replace `AGENTS.md`, `README.org`, `CLAUDE.md`, or anything in `.claude/`.
- It mirrors and condenses the Claude-facing notes into OpenCode-friendly references.
- The original files remain the canonical source material.

Layout:

- `.opencode/AGENTS.md` - OpenCode operating rules for this repo
- `.opencode/commands/prime.md` - lightweight DotCortex session orientation workflow
- `.opencode/commands/handoff.md` - fresh-window handoff workflow for DotCortex work
- `.opencode/commands/commit.md` - structured DotCortex commit workflow
- `.opencode/commands/verify.md` - confirm a tool exists here and inspect help output
- `.opencode/commands/reflect.md` - manual OpenCode session reflection workflow
- `.opencode/commands/todo.md` - route and review TODO work in DotCortex tracking files
- `.opencode/commands/tangle-one.md` - tangle a single owning DotCortex org file quickly
- `.opencode/commands/tangle-and-stow-x230.md` - one-file tangle plus X230 apply flow
- `.opencode/commands/tangle-and-stow-t480s.md` - one-file tangle plus T480s apply flow
- `.opencode/commands/loom.md` - document the `/loom` Loom-first convention and how to route Loom-aware requests
- `.opencode/commands/full-rebuild-x230.md` - full X230 tangle and stow rebuild flow
- `.opencode/commands/full-rebuild-t480s.md` - full T480s tangle and stow rebuild flow
- `.opencode/commands/configure-antigravity.md` - Antigravity configuration workflow through DotCortex
- `.opencode/commands/nexus-update.md` - refresh local NEXUS mirrors before comparative audits
- `.opencode/commands/skill-sync.md` - audit and sync missing OpenCode-local workflows, skills, and guidance
- `.opencode/notes/source-map.md` - where each note came from
- `.opencode/notes/dotcortex-reference.md` - merged working reference
- `.opencode/memory/README.md` - OpenCode memory index adapted from Claude memories
- `.opencode/memory/user-metsatron.md` - user workflow and communication preferences
- `.opencode/memory/task-tracking.md` - canonical TODO and progress tracking locations
- `.opencode/memory/wezterm-host-sendtext.md` - WezTerm host-pane and send_text behavior
- `.opencode/memory/helmcortex-context.md` - cross-project doctrine and architecture context
- `.opencode/memory/pvox-workflow.md` - stateless `pvox` speaking workflow and voice conventions
- `.opencode/memory/antigravity.md` - Antigravity ownership, package source, paths, and defaults
- `.opencode/skills/helmcortex-pvox/SKILL.md` - speak through VoxForge `pvox` with Flatpak Pied models
- `.opencode/skills/antigravity-config/SKILL.md` - manage Antigravity from DotCortex source files
- `.opencode/skills/context-hygiene/SKILL.md` - keep OpenCode context lean and delegate heavy exploration
- `.opencode/skills/dotcortex-gotchas/SKILL.md` - central troubleshooting notes for known DotCortex failures
- `.opencode/skills/dotcortex-multihost/SKILL.md` - machine overlays, mounts, and HelmCortex boundary guidance
- `.opencode/skills/dotcortex-loom/SKILL.md` - mirrored DotCortex skill for OpenCode use
- `.opencode/skills/dotcortex-packages/SKILL.md` - package-manager architecture and add-a-new-manager guidance
- `.opencode/skills/dotcortex-package-manifests/SKILL.md` - focused package manifest operations skill
- `.opencode/skills/dotcortex-bootstrap/SKILL.md` - fresh machine and recovery bootstrap skill
- `.opencode/templates/repo-conventions.md` - reusable repo conventions template
- `.opencode/templates/task-patterns.md` - reusable task execution patterns
- `.opencode/workflows/dotcortex-edit-flow.md` - safe edit, tangle, and stow flow
- `.opencode/workflows/bootstrap-checklist.md` - fresh machine and bootstrap checklist
- `.opencode/workflows/source-adaptation.md` - Bruce Lee filter for adapting external agent ideas into OpenCode-owned guidance

Current audit note:

- `.claude/` is present and used as read-only source material
- `.agents/` and `.codex/` are not present in this repo right now, but `skill-sync` should still treat them as optional delta sources when they appear locally or via adjacent repos
