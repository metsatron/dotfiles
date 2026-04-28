---
name: pixelcortex-catalog
description: Add or update a game entry in PixelCortex — catalog a game under the correct platform, enforce curation doctrine and schema compliance.
---

*description: Add or update a game entry in PixelCortex — catalog a game under the correct platform, enforce curation doctrine and schema compliance.*

> **Model:** `gpt-5.4` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# PixelCortex Catalog

Use this skill when adding a new game to PixelCortex or updating an existing game entry.

## Curation Gate

Before creating any entry, confirm at least one of these is true:
- Game is **actively being played**
- Game has been **completed**
- Game has **real save data** showing hours invested (not auto-generated SRAM)
- Game has **mods, patches, or translations** worth documenting
- Game is **planned for imminent return** (within ~2 weeks)

If none apply, do not create the entry. PixelCortex is curated, not exhaustive.

## Steps

### 1. Identify Platform

Read `systems/` to find the correct platform folder. Exact casing required. Common platforms: `nes/`, `snes/`, `psx/`, `ps2/`, `ps3/`, `ps4/`, `switch/`, `gba/`, `nds/`, `gc/`, `wii/`, `dreamcast/`, `pc/`, `linux/`, `megadrive/`, `genesis/`, `arcade/`, etc.

### 2. Check Schema

Read `meta/canon_schema.md` for the frontmatter schema. If the schema file is empty, use this minimal structure:

```yaml
---
title: Game Title
platform: Platform
status: backlog | active | completed | shelved
date_added: YYYY-MM-DD
date_completed: # if completed
tags: [genre, series, relevant-tags]
---

# Game Title

## Notes

Personal play notes, observations, why this game matters.

## Links

- Mods: [[mods/...]] (if applicable)
- FAQ: [[faq/...]] (if applicable)
- Backlog: [[backlog/sacred_canon]] or [[backlog/important_canon]] (if vowed)
```

### 3. Write Entry

Create the file at `systems/{platform}/{game-slug}.md` using kebab-case for the slug. Write frontmatter and body following the schema.

### 4. Cross-Link

- If the game is vowed, ensure it appears in `backlog/sacred_canon.md` or `backlog/important_canon.md`
- If mods exist, link from `mods/index.md`
- If a FAQ or guide exists, link from `faq/index.md`
- If it is a port, link from the relevant `ports/{port}/` entry

### 5. Verify

Re-read the entry after writing. Confirm frontmatter parses, cross-links resolve, and no empty sections remain.

## PixelForge Scripts

PixelCortex entries can be seeded or bulk-generated from PixelForge scripts in `FORGE/PixelForge/scripts/`:

| Script | Purpose |
|--------|---------|
| `generate_pixelcortex_game_dirs.py` | Auto-generate game folders under `systems/` from Playnite/emulationstation data. Use `--min-playcount N` to enforce curation gate. Always `--dry-run` first. |
| `parse_playnite_gamelists.py` | Scrape Playnite JSON exports into markdown. Use `--platform-map platform_mapping.json`. |
| `parse_emulationstation_gamelists.py` | Parse EmulationStation gamelists.xml into markdown. |
| `merge_playnite_databases.py` | Merge multiple Playnite export JSONs. |
| `parse-completionator-import.py` | Parse Completionator CSV export into `completion/completionator-import-parsed.md`. |
| `gog-canonicalizer.py` | Normalize GOG directory names. `--dry-run` first, then `--commit --log`. |
| `gog-feed-sync.py` | Sync GOG torrent feed data. |
| `ps4-pkg-indexer.py` | Index PS4 PKG files. |
| `switch-yuzu-db.py` / `switch-yuzu-md.py` | Parse Yuzu Switch database into markdown. |
| `genshin-export.py` | Export Genshin Impact account data for gacha tracking. |
| `game-dl-migrator` | Scan `~/Downloads` for completed game downloads, validate and migrate to pool paths, run downstream PixelForge scripts, detect PS4 duplicates. Elevated to `FORGE/bin/` (on PATH). |
| `game-history-indexer` | Index game-investigation browser tabs from tab snapshot JSON (in `FORGE/bin/`). |

These scripts are FORGE tools — never invoke them from within PixelCortex. Reference them when a bulk operation or data import is needed.

## Rules

- One file per game per platform. Multi-platform games get separate entries.
- Kebab-case slugs only. No spaces.
- Never create platform folders that do not already exist under `systems/` — flag to Mètsàtron if a platform is missing.
- Preserve all existing entries — never overwrite or condense another game's record.

