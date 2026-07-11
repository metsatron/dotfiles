---
name: context-hygiene
description: Keep context lean and delegate heavy exploration.
---

# Context Window Hygiene

## Principles

1. **Keep instruction files lean** — project-level instruction files (`AGENTS.md`, `CLAUDE.md`) are always loaded. Keep them under 100 lines. Move reference material to skills that load on demand.
2. **Skills load on demand** — put gotchas, package tables, multi-machine details, and other reference content in skills rather than always-loaded files.
3. **Delegate heavy exploration** — large searches, multi-file reads, and independent tasks should go to subagents or be scoped tightly to avoid ballooning context.

## When to Use a Fresh Session

- Task is completely unrelated to current work
- Context is polluted with stale file contents from earlier exploration
- Session has been running for a very long time with many tool calls and responses feel sluggish

## When to Delegate to Subagents

- Searching across 5+ files for a pattern
- Exploring unfamiliar parts of the codebase
- Running tests or builds that produce verbose output
- Any independent task that does not need the main thread context

## Skill Loading Strategy

Load skills only when the task matches:

- Debugging stow/tangle/guix issues -> `dotcortex-gotchas`
- Adding packages or package managers -> `dotcortex-packages`
- Multi-machine setup, overlay scoping, bootstrap -> `dotcortex-multihost`
- This skill itself is meta — load it when reviewing context efficiency
