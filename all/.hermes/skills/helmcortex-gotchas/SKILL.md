---
name: helmcortex-gotchas
description: Known quirks, traps, and non-obvious behaviours in HelmCortex. Load at session start and whenever unexpected behaviour is encountered.
---

*description: Known quirks, traps, and non-obvious behaviours in HelmCortex. Load at session start and whenever unexpected behaviour is encountered.*

> **Model:** `gpt-5.4-mini` | **Effort:** `low` | **Delegate:** `mini`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# HelmCortex Gotchas

## Architecture

- **HelmCortex and DotCortex are sibling repos** — HelmCortex never lives inside DotCortex and vice versa. Root: `$HOME/HelmCortex` and `$HOME/.dotfiles` (or `$HOME/.dotcortex`). Do not conflate them.
- **Two machines, one vault**: ThinkPad X230 is primary (`$HOME/HelmCortex`). T480S accesses via mount at `$HOME/mnt/x230/HelmCortex`. Hostname-aware paths required in all scripts. Check `hostname` before assuming path.
- **Git repo root detection**: use `git rev-parse --show-toplevel` to find HelmCortex root from any subdirectory — do not hardcode paths.


## Obsidian CLI

- **dbus warnings are cosmetic**: `obsidian` CLI may emit dbus-related warnings before producing output. Strip with `2>/dev/null` and evaluate actual output only.
- **Vault name vs path**: The CLI uses `--vault HelmCortex` (vault name as known to Obsidian) not the filesystem path. Do not pass filesystem paths to `--vault`.

## pvox / VoxForge

- **Pied Flatpak for model management only**: Pied handles voice model downloads. All configuration, routing, and orchestration is pvox's domain — never use Pied for programmatic voice operations.
- **Player cascade**: paplay → aplay → ffplay → pw-play. If playback fails silently, check which player backends are available.
- **Voice models path**: `~/.var/app/com.mikeasoft.pied/data/pied/models/`

## File Operations

- **ISO dates required** in time-stream filenames: `YYYY-MM-DD-description.md` — not `description-2026.md` or any other order.
- **No spaces in directory names** — use underscores or CamelCase. The filesystem is case-sensitive.
- **docs/ placement**: Always sibling to `bin/` at parent level. A script at `FORGE/VoxForge/bin/pvox` has its docs at `FORGE/VoxForge/docs/pvox.md` — never `FORGE/VoxForge/bin/docs/pvox.md`.

## helmcortex-sync

- Sync target is 3+ drives minimum. If fewer drives are mounted, sync proceeds to available targets — it does not fail, but it also does not guarantee full redundancy. Verify mounted drive count before treating sync as complete backup.

## Context Window

- LOGS directories can be massive. Never glob or read LOGS recursively without a specific target path. Use subagents for any task requiring broad LOGS exploration.
- ROOTS and CORTEX are stable — safe to read selectively. LOGS are always in flux.

