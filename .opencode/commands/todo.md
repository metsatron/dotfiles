# todo - DotCortex Task Routing

Use this when routing, reviewing, or updating TODO items related to DotCortex
work.

## Subcommands

- `add <scope> <task>`
- `done <search text>`
- `review`

## Scope Routing

- `dot`, `shell`, `wezterm`, `nala`, `loom`, or `stow` -> `LOGS/TODO/DotCortex.md`
- `x230` -> `LOGS/TODO/Machines/ThinkPad-X230.md`
- `t480s` -> `LOGS/TODO/Machines/ThinkPad-T480s.md`

If a task clearly belongs to HelmCortex or FontCortex instead, route it to the
matching TODO file rather than forcing it into DotCortex.

## Steps

1. Identify the right TODO file from the scope.
2. For `add`, append a new checkbox item under the most relevant section.
3. For `done`, find the matching open item and mark it complete with today's
   date.
4. For `review`, read the main DotCortex and machine TODO files and produce a
   compact summary of open work and stale items.

## Rules

- use Obsidian Tasks format: `- [ ]` and `- [x] ... ✅ YYYY-MM-DD`
- keep TODO files action-oriented rather than research-oriented
- if an item is really research, suggest moving it to a research or evaluation
  flow instead of letting TODOs become a dumping ground
