# /todo — DotCortex Task Routing

Manage TODO items related to DotCortex work. Subcommand: $ARGUMENTS

## Subcommands

### `add <scope> <task description>`
Route a new task to the correct TODO file based on scope keyword:
- `dot`, `shell`, `wezterm`, `nala`, `loom`, `stow`, `style` → `LOGS/TODO/DotCortex.md`
- `x230` → `LOGS/TODO/Machines/ThinkPad-X230.md`
- `t480s` → `LOGS/TODO/Machines/ThinkPad-T480s.md`

If a task clearly belongs to HelmCortex or FontCortex instead, say so and suggest routing it there.

Use `obsidian append path="<target-file>" content="- [ ] <task description>"` to add the task. If the task belongs under a specific section heading, first use `obsidian read` to find the right location, then use the `Edit` tool to insert it there instead.

### `done <search text>`
1. Use `obsidian search query="<search text>" limit=10` to find the item across TODO files, then `obsidian read` the matching file
2. Use the `Edit` tool to mark it complete: `- [x] <task> ✅ YYYY-MM-DD`
3. If the file has a Progress section for today, add it there too
4. If no Progress section for today exists, create one at the top (after header) using the `Edit` tool:
   ```
   ## Progress — YYYY-MM-DD (Claude Code Session)
   - [x] <task> ✅ YYYY-MM-DD
   ```
5. If no match found, report it

### `review`
1. Read all DotCortex-relevant TODO files using `obsidian read` for each:
   - `LOGS/TODO/DotCortex.md`
   - `LOGS/TODO/Machines/ThinkPad-X230.md`
   - `LOGS/TODO/Machines/ThinkPad-T480s.md`
2. Count open `- [ ]` items per file
3. Flag stale items (in a Progress section older than 30 days with no completion date)
4. Flag research-shaped items ("Investigate", "Evaluate", "Explore", "Research") that should be in `LOGS/Antigravity/projects/` or `LOGS/Research/` instead
5. Output compact summary (under 30 lines)

## Rules
- Always use Obsidian Tasks format: `- [ ]` open, `- [x] ✅ YYYY-MM-DD` done
- TODO files are action-oriented — concrete deliverables, not research
- TODO files live in `~/HelmCortex/LOGS/TODO/` (HelmCortex is the knowledge base, DotCortex is the dotfiles repo)
- Use `obsidian` CLI for reading/searching when Obsidian is running; fall back to direct file reads if CLI is unavailable
- When in doubt about scope routing, ask
