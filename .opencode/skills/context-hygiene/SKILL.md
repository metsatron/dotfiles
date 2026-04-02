---
name: context-hygiene
description: Context window hygiene for OpenCode - when to narrow scope, refresh reads, and delegate heavy exploration.
---

# Context Hygiene For OpenCode

Use this skill when the task is broad, search-heavy, browser-heavy, or the session is starting to feel bloated or stale.

## Principles

1. `AGENTS.md` and `.opencode/AGENTS.md` hold durable repo rules. Keep bulky reference material in skills and workflows.
2. Load context just in time. Do not read whole subsystems when a few files will do.
3. Re-read files after edits or after the user changes the worktree. Do not trust stale assumptions.
4. Use subagents to protect main context when the search space or output volume is large.
5. Use the todo list for multi-step work so the main thread stays focused.

## When To Narrow Or Reset Approach

- before switching to an unrelated task in the same session
- after a major milestone such as a commit, rebuild, or bug resolution
- when answers start repeating earlier context instead of current file state
- when the task has crossed into 5+ files or multiple subsystems
- when browser output or command output is getting too large to reason about comfortably

OpenCode does not expose Claude's `/compact` or hook system here, so the equivalent move is: delegate, start a fresh session for unrelated work, or re-read only the active files.

## When To Delegate

- codebase exploration across many files or naming conventions
- heavy browser inspection on content-dense pages
- verbose test, build, or diagnostic runs where only the summary matters
- independent research that can return a compact conclusion to the main thread

Use the `explore` subagent for targeted codebase discovery and the `general` subagent for broader multi-step research.

## Browser Defaults

- prefer `browser_query` with targeted selectors or `mode: "page_text"` before taking a full snapshot
- treat `browser_snapshot` as a structural tool, not the default read path on heavy pages
- filter `browser_console` when possible so framework noise does not flood context
- for long articles or dense app pages, delegate browser inspection and consume the summary

## Durable Write Targets

- stable facts and preferences -> `.opencode/memory/*.md`
- repeatable procedures -> `.opencode/skills/*/SKILL.md`
- lightweight manual recipes -> `.opencode/commands/*.md` or `.opencode/workflows/*.md`

## Do Not Port Blindly

- no fabricated hook support
- no automatic memory persistence claims
- no client-specific UI or slash-command behavior presented as active here

## Skill Routing

- stow, tangle, Guix, or bootstrap failures -> `dotcortex-gotchas`
- package-manager architecture or adding a new manager -> `dotcortex-packages`
- multi-machine overlays or HelmCortex mount questions -> `dotcortex-multihost`
- normal DotCortex operations -> `dotcortex-loom`
