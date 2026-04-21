# /todo — DotCortex Task Routing

Manage TODO items related to DotCortex work. Subcommand: $ARGUMENTS

## Subcommands

### `add <scope> <task description>`
Route a new task to the correct TODO file based on scope keyword:
- `dot`, `shell`, `wezterm`, `nala`, `loom`, `stow`, `style` → `LOGS/TODO/DotCortex.md`
- `x230` → `LOGS/TODO/Machines/ThinkPad-X230.md`
- `t480s` → `LOGS/TODO/Machines/ThinkPad-T480s.md`

If a task clearly belongs to HelmCortex or FontCortex instead, say so and suggest routing it there.

Add as `- [ ] <task description>` under the most relevant section heading. If unsure which section, add under the first relevant heading.

### `done <search text>`
1. Search TODO files for an open item matching the search text
2. Mark it complete: `- [x] <task> ✅ YYYY-MM-DD`
3. If no match found, report it

### `review`
1. Read all DotCortex-relevant TODO files:
   - `LOGS/TODO/DotCortex.md`
   - `LOGS/TODO/Machines/ThinkPad-X230.md`
   - `LOGS/TODO/Machines/ThinkPad-T480s.md`
2. Count open `- [ ]` items per file
3. Flag stale items (older than 30 days with no progress)
4. Flag research-shaped items ("Investigate", "Evaluate", "Explore") that should be moved elsewhere
5. Output compact summary (under 30 lines)

## Rules
- Use Obsidian Tasks format: `- [ ]` open, `- [x] ✅ YYYY-MM-DD` done
- TODO files are action-oriented — concrete deliverables, not research
- TODO files live in `~/HelmCortex/LOGS/TODO/` (HelmCortex is the knowledge base, DotCortex is the dotfiles repo)
- When in doubt about scope routing, ask
