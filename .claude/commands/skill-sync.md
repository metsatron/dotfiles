# /skill-sync — Claude Code Layer Sync Audit

Check whether DotCortex's `.claude` layer is missing commands, skills, or guidance that already exists in `.opencode`, `.codex`, or `.agents` (locally or in `~/HelmCortex`), then adapt the useful pieces.

## Purpose

Use when the `.claude/` layer feels stale relative to peer overlays, or when asked to sync.

The goal is not parity — it's a Claude Code layer that reflects:
- Claude Code's real capabilities (hooks, skills, commands, MCP)
- DotCortex doctrine and local workflow
- actual differences between Claude Code and other clients

## Source Priority

1. `CLAUDE.md` — repo-level instructions
2. `.claude/` — canonical Claude Code layer
3. `.opencode/` and `.codex/` as delta sources for missing concepts
4. `~/HelmCortex/.claude/` for cross-repo command patterns

## Audit Scope

Compare `.claude/commands/`, `.claude/skills/`, `.claude/settings.local.json` against:
- `.opencode/commands/` and `.opencode/skills/`
- `.codex/commands/` and `.codex/skills/` (if present)
- `~/HelmCortex/.claude/commands/`
- `~/HelmCortex/.opencode/commands/`
- `~/HelmCortex/.codex/commands/`

## Steps

1. Inventory current `.claude` commands and skills
2. Inventory peer overlays (local + HelmCortex)
3. Identify gaps — classify each as `port`, `adapt`, or `skip`
4. Implement `port` and `adapt` items
5. Rewrite for Claude Code reality (real hooks, real $ARGUMENTS, real skill registration)
6. Report what was added, skipped, and why

## Rules
- Do not copy source text blindly — adapt for Claude Code conventions
- Skip HelmCortex-specific workflows (Obsidian WebClipper, WarMap, Antigravity layers)
- Skip features that depend on capabilities Claude Code lacks
- Keep commands concise and action-oriented
