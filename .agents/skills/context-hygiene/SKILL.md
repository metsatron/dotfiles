---
name: context-hygiene
description: Keep OpenCode context lean and delegate heavy exploration.
---

# Context Window Hygiene

## Principles

1. **CLAUDE.md is always loaded** — keep it under 100 lines. Move reference material to skills.
2. **Skills load on demand** — put gotchas, package tables, multi-machine details, and other reference content in skills.
3. **Memory files persist across sessions** — use `~/.claude/projects/*/memory/` for stable patterns, not session-specific state.
4. **Subagents protect context** — delegate large searches, multi-file exploration, and independent tasks to subagents rather than consuming main context.

## When to Compact

- After completing a major task milestone (commit, stow cycle, debug resolution)
- When context feels sluggish or repetitive
- Before starting an unrelated task in the same session
- **After 30+ exchanges or when responses feel sluggish/overly cautious** — run `/compact` to reset working context. Quality degrades with context bloat, not just cost.

## When to Use a Fresh Session

- Task is completely unrelated to current work
- Context is polluted with stale file contents from earlier exploration
- Session has been running for 30+ minutes with many tool calls

## When to Delegate to Subagents

- Searching across 5+ files for a pattern
- Exploring unfamiliar parts of the codebase
- Running tests or builds that produce verbose output
- Independent tasks that don't need main context
- **Browser inspection on complex pages** — `read_page`, `browser_snapshot`, and `get_page_text` on content-heavy pages dump thousands of tokens into context. Delegate to an Explore or general-purpose subagent and consume only the summary.

## Browser Tool Smart Defaults

Browser automation tools (claude-in-chrome) produce verbose output by default. Always use filtering parameters:

- **`read_page`**: Use `filter: "interactive"` unless you specifically need non-interactive elements. Full `"all"` dumps include every text node, image, and hidden element.
- **`read_console_messages`**: Always provide a `pattern` parameter (e.g., `"error|warn"`, `"MyApp"`). Unfiltered console output includes framework noise, analytics pings, and irrelevant logs.
- **`read_network_requests`**: Always provide a `urlPattern` (e.g., `"/api/"`, `"graphql"`). Without it, you get every static asset, font, tracker, and analytics request.
- **`browser_snapshot`**: Prefer `read_page` with `filter: "interactive"` when you only need to find clickable elements. Reserve `browser_snapshot` for when you need full page structure.
- **`get_page_text`**: Delegate to a subagent for long articles. Only call directly for short pages where you need the full text in main context.

## Session Persistence

- **SessionStart hook auto-injects TODO context** — DotCortex TODO and machine-specific TODO from the HelmCortex vault are loaded into session context automatically. No manual loading needed.
- **PreCompact hook auto-saves MEMORY.md** — before `/compact` or context wipes, the hook dumps MEMORY.md content to `LOGS/TODO/DotCortex.md` in the vault as a timestamped block, then truncates MEMORY.md. No manual persist step needed before compacting.
- **Stop hook nudges at 15 responses** — a counter-based hook reminds you to run `/reflect` every 15 responses. This is a nudge, not enforcement.
- **`/reflect` is still manual** — run it at natural session breakpoints: task complete, switching domains, before ending a long session. It analyses the session, persists facts/preferences to MEMORY.md, and promotes durable discoveries to the HelmCortex vault.
- **Autonomous skill creation threshold**: Create a skill candidate when a novel multi-step solution was discovered (>3 tool calls), a new gotcha was found not already in dotcortex-gotchas, or a reusable workflow emerged that would save time in future sessions.
- **MEMORY.md vs skills**: MEMORY.md is for facts and observations (file paths, tool behaviours, environment quirks). Skills are for procedures (how to do X). If it's a "how", make it a skill. If it's a "what", put it in MEMORY.md.

## Skill Loading Strategy

Load skills only when the task matches:
- Debugging stow/tangle/guix issues -> `dotcortex-gotchas`
- Adding packages or package managers -> `dotcortex-packages`
- Multi-machine setup, overlay scoping, bootstrap -> `dotcortex-multihost`
- This skill itself is meta — load it when reviewing context efficiency
