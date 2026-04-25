---
name: helmcortex-structure
description: HelmCortex pillar and archive layout, GoldenAge Loom flow, key scripts and paths. Load for any task involving HelmCortex navigation, file placement decisions, or cross-pillar moves.
---

*description: HelmCortex pillar and archive layout, GoldenAge Loom flow, key scripts and paths. Load for any task involving HelmCortex navigation, file placement decisions, or cross-pillar moves.*

> **Model:** `gpt-5.4-mini` | **Effort:** `low` | **Delegate:** `mini`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# HelmCortex Structure

## The Five Pillars

| Pillar | Function | Nature |
|--------|----------|--------|
| **FORGE** | Tools, builders, scripts. All automation lives here. | Mycelium — underground network that processes everything |
| **LOGS** | Time-stream and traces. Raw AI chats, dreams, exports, TODOs. | Raw material — fallen leaves, uncomposted matter |
| **ROOTS** | Indexed libraries and datasets (stable). | Root system — stable, deep, nutrient-storing |
| **CORTEX** | Curated canon (current truth). Arranged doctrine, definitions, dashboards. | Trunk and branches — visible, structured, living tree |
| **CORE** | Emotional, spiritual, mythic cores. ErosCore, NadaCore, SteinerCore. | Heartwood — oldest, densest, most essential |

## Sacred Archives

| Archive | Function |
|---------|----------|
| **NADA** | Sacred medicine archives — LumenAstra, Makína Kènè materials |
| **NEXUS** | API keys, integration secrets, rsync configuration |
| **VOX** | Voice and TTS assets — raw voice models |
| **WOMB** | Dream and ceremonial logs — embryons, seeds, sacred orders |

## GoldenAge Loom Flow

```
LOGS → (FORGE) → ROOTS → CORTEX
        ↑                    ↓
        └────── feedback ─────┘
```

- LOGS: receive raw material (chat exports, dream logs, voice transcripts)
- FORGE: processes it (deblobbing, chunking, slicing, indexing)
- ROOTS: stable indexed form
- CORTEX: curated, canonical, current-truth version
- When canon is superseded, it moves back to ROOTS for archiving

## Sub-Projects

| Project | Location | Function |
|---------|----------|----------|
| **TimeArk** | FORGE/TimeArk, LOGS/divinations, ROOTS/TimeArk, CORTEX/TimeArk | Temporal tracking, Vedic Horas, Hebrew Calendar, divinations |
| **ShrineOfAstra** | FORGE/ShrineOfAstra, CORTEX/ShrineOfAstra | Book of Astra, AstraVault, consort lineage archives |
| **PixelForge** | FORGE/PixelForge | Gaming scripts — Genshin, PS4, GOG, Switch automation |
| **VoxForge** | FORGE/VoxForge | Sonic body layer — pvox voice engine |
| **AstraCortex** | CORTEX/GoldenAge_Loom/AstraCortex | Book of Astra canonical materials |
| **NadaCortex** | CORTEX/GoldenAge_Loom/NadaCortex | LumenAstra, Makína Kènè, PrayerCodex, IcaroCodex |
| **SteinerCortex** | CORTEX/GoldenAge_Loom/SteinerCortex | SystemCodex (WarMap lives here), CoolCodex, doctrine |

## Key Scripts

| Script | Path | Function |
|--------|------|----------|
| `helmcortex-sync` | FORGE/bin/helmcortex-sync | Backup/mirror across drives |
| `helmcortex-readme-indexer` | FORGE/bin/helmcortex-readme-indexer | Generate README indexes |
| `chatgpt-md-pipeline` | FORGE/bin/chatgpt-md-pipeline | Deblob ChatGPT exports |
| `chatgpt-memory-pipeline` | FORGE/bin/chatgpt-memory-pipeline | Process LumenAstra memories |
| `pvox` | FORGE/VoxForge/bin/pvox | Voice engine |
| `claude-code-md-pipeline` | FORGE/bin/claude-code-md-pipeline | Process Claude Code exports |
| `telegram-process-exports` | FORGE/bin/telegram-process-exports | Telegram → MD |
| `gab_process_hars.sh` | FORGE/bin/ | Gab.AI HAR extraction |

## Path Rules

- ISO dates in filenames and frontmatter for time-stream notes (YYYY-MM-DD)
- No spaces in directory names — use underscores or CamelCase
- Case-sensitive filesystem — respect exact casing
- `docs/` and `Images/` always live as siblings to `bin/` and `scripts/` at parent level — **never inside them**
- SoulPrints live in `CORTEX/GoldenAge_Loom/SteinerCortex/`
- LOGS are never final knowledge — they are raw material awaiting FORGE processing

