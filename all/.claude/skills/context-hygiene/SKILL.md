---
name: context-hygiene
description: Context window hygiene — when to compact, clear, and delegate to subagents
model: claude-sonnet-4-6
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

## When to Compact

- After completing a major task milestone (commit, stow cycle, debug resolution)
- Before starting an unrelated task in the same session
- After 30+ exchanges or when responses feel sluggish — run `/compact` to reset working context

## Browser Tool Smart Defaults

`claude-in-chrome` tools produce verbose output by default. Always use filtering parameters:

- **`read_page`**: Use `filter: "interactive"` unless you need non-interactive elements. `"all"` dumps every text node and hidden element.
- **`read_console_messages`**: Always provide a `pattern` (e.g., `"error|warn"`, `"MyApp"`). Unfiltered output includes framework noise and analytics.
- **`read_network_requests`**: Always provide a `urlPattern` (e.g., `"/api/"`, `"graphql"`). Without it you get every static asset, font, and tracker.
- **`browser_snapshot`**: Prefer `read_page` with `filter: "interactive"` when you only need clickable elements. Reserve `browser_snapshot` for full page structure.
- **`get_page_text`**: Delegate to a subagent for long articles. Call directly only for short pages where you need the full text in main context.

## Claude Session Persistence

- **SessionStart hook** auto-injects the DotCortex TODO and machine-specific TODO from the vault into session context. No manual loading needed.
- **PreCompact hook** auto-saves MEMORY.md content to `LOGS/TODO/DotCortex.md` in the vault before compacting, then truncates MEMORY.md.
- **Stop hook** counts responses and nudges you to run `/reflect` every 15 responses.
- **`/reflect` is still manual** — run it at natural breakpoints: task complete, switching domains, before ending a long session.

## MEMORY.md vs Skills

- **MEMORY.md** is for facts and observations (file paths, tool behaviours, environment quirks, user preferences).
- **Skills** are for procedures (how to do X).
- If it is a "how", make it a skill. If it is a "what", put it in MEMORY.md.

## Autonomous Skill Creation Threshold

Create a skill candidate when any of these apply:
- A novel multi-step solution was discovered (more than 3 tool calls, not covered by an existing skill)
- A new gotcha was found that is not already in `dotcortex-gotchas`
- A reusable workflow emerged that would save significant time in future sessions
