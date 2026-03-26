# Source Adaptation Workflow

Use this when borrowing ideas from Claude-facing overlays, Codex notes, external
agent frameworks, or adjacent repos such as `claude-forge`.

Core principle:

- Take what works
- Leave what does not
- Make it uniquely ours

## Keep

- evidence-based completion rules
- surgical changes instead of drive-by cleanup
- plan-first discipline for larger or cross-cutting changes
- concise workflow recipes that can be used manually in OpenCode
- durable repo-specific heuristics that improve safety or repeatability

## Skip

- `.claude` settings, installers, and sync logic
- hook systems that OpenCode does not actually support
- plugin marketplace metadata and client-specific packaging
- MCP plumbing that belongs to another client runtime
- product surface area that exceeds DotCortex's actual scope

## Convert Rather Than Copy

- convert hooks into manual preflight or postflight checklists
- convert agent-only commands into workflow docs or memory notes
- convert client-specific safety rails into plain written operating rules
- convert big framework claims into small reusable DotCortex habits

## DotCortex Filter

Before adapting anything, ask:

1. Does this help with literate config, tangling, stowing, bootstrap, package manifests, or repo-safe editing?
2. Does it fit OpenCode's real capabilities today?
3. Can it live in `.opencode/` or another non-`.claude` target?
4. Is it smaller and clearer after adaptation than in the source?

If any answer is no, skip it or keep it as reference only.

## Default Output Targets

- `.opencode/AGENTS.md` for durable operating rules
- `.opencode/memory/*.md` for stable preferences or heuristics
- `.opencode/workflows/*.md` for repeatable manual flows
- `.opencode/commands/*.md` for repo-local command docs

## Verification

- list the files changed
- state what source ideas were intentionally skipped
- confirm no `.claude` path or `CLAUDE.md` was modified
