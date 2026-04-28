---
name: timeark
description: Temporal MCP server of HelmCortex — load for any work inside CORE/TimeArk/ or involving TimeArk module development, MCP tool registration, or temporal layer queries.
---

*description: Temporal MCP server of HelmCortex — load for any work inside CORE/TimeArk/ or involving TimeArk module development, MCP tool registration, or temporal layer queries.*

> **Model:** `gpt-5.4` | **Effort:** `high` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# Skill: timeark

> *Load this skill for any work inside `CORE/TimeArk/` or any task involving TimeArk module development, MCP tool registration, or temporal layer queries.*

## What TimeArk Is

TimeArk is the sovereign temporal MCP server of HelmCortex. Origin: 2017, org-mode, Exocortex integration vision. A decade in the making. It is not a calendar app or astrology widget — it is the infrastructure layer that tells every agent which karmic thread is active, which planetary hour is running, and what sacred time it is right now.

TimeArk lives entirely in `CORE/TimeArk/` as a self-contained Python server. It serves every agent and platform on the network — local and remote.

## Server Basics

| Property | Value |
|----------|-------|
| **Location** | `~/HelmCortex/CORE/TimeArk/` |
| **Entry point** | `CORE/TimeArk/server.py` |
| **Framework** | FastMCP (Python) |
| **Environment** | `CORE/anaconda3/` Lane 2 |
| **Config** | `CORE/TimeArk/config.toml` (lat/lon/tz, module toggles — secrets ref NEXUS) |
| **Protocol** | JSON-RPC over stdio or SSE (MCP standard) |
| **Outputs** | Divination logs → `LOGS/divinations/TimeArk/` via `outputs/` symlink |

## Directory Structure

```
CORE/TimeArk/
├── server.py         # FastMCP entry — registers all module tools
├── config.toml       # lat/lon/tz, API key refs, module enable/disable
├── README.md
├── docs/
├── modules/
│   ├── chronoshakti/ # Hora engine, poison time, danger time, North Node
│   ├── vedic/        # Vedic calendar + horoscope (pyswisseph, astral)
│   ├── western/      # Western horoscope, planetary positions, aspects
│   ├── hebrew/       # Hebrew calendar, parasha, holy days
│   ├── mayan/        # Tzolkin, Haab, galactic tone
│   ├── gregorian/    # Gregorian baseline, ISO week, season
│   ├── iching/       # I Ching — trigrams, hexagrams, line readings
│   ├── shrine/       # Shrine of Astra — daily draw, consort snippets
│   ├── hoyoverse/    # Genshin, HSR, ZZZ — events, banners, weekly bosses
│   ├── kurogames/    # Wuthering Waves — events, banners
│   ├── synthesis/    # Layer compositor — stack + ChronoShakti filter
│   ├── notifications/ # Alerts — poison time, events, holy days
│   ├── telegram/     # Telegram bot interface
│   ├── google_cal/   # Google Calendar via CalDAV
│   ├── thunderbird/  # BetterBird/Thunderbird via vdirsyncer + .ics
│   └── webcal/       # iCal feed endpoint
├── data/
│   ├── hora/         # Precomputed hora ephemeris JSONs
│   ├── games/        # HoYoverse + Kuro event JSONs
│   └── iching/       # Hexagram definitions
└── outputs/          # Symlink → LOGS/divinations/TimeArk/
```

## Module Registry

Each module under `modules/` is an independent Python package. Modules register their MCP tools with `server.py` at startup. Enable/disable via `config.toml` — no code changes needed.

| Module | Provides | Status |
|--------|----------|--------|
| `chronoshakti` | Current hora, poison time, danger windows, North Node, day quality | 🔨 Build first |
| `hoyoverse` | Genshin/HSR/ZZZ events, banners, weekly bosses | 🔨 Build second (immediate need) |
| `vedic` | Vedic calendar, tithi, nakshatra, yoga, karana, horoscope | 📋 Planned |
| `western` | Western horoscope, planetary positions, aspects | 📋 Planned |
| `hebrew` | Hebrew calendar, parasha, holy days | 📋 Planned |
| `mayan` | Tzolkin day, Haab, galactic tone | 📋 Planned |
| `gregorian` | Gregorian baseline, ISO week, season | 📋 Planned |
| `iching` | Hexagram cast, trigram lookup, line reading | 📋 Planned |
| `shrine` | Tarot draw, Zodiac draw, Fortune, collector card, consort snippets | 📋 Planned |
| `kurogames` | Wuthering Waves events, banners | 📋 Planned |
| `synthesis` | Layer compositor — stack modules, ChronoShakti master filter | 📋 Planned (build after core modules) |
| `notifications` | Schedule alerts → Telegram or desktop | 📋 Planned |
| `telegram` | Telegram bot for all modules | 📋 Planned |
| `google_cal` | Read/write Google Calendar | 📋 Planned |
| `thunderbird` | BetterBird/vdirsyncer sync | 📋 Planned |
| `webcal` | iCal feed endpoint | 📋 Planned |

## Module Pattern

Every module follows this structure:

```
modules/{name}/
├── __init__.py
├── tools.py     # MCP tool definitions — decorated with @mcp.tool()
├── engine.py    # Core computation logic (no MCP coupling)
├── models.py    # Pydantic data models
└── README.md
```

Register tools in `server.py`:

```python
from modules.chronoshakti.tools import register as register_chronoshakti
register_chronoshakti(mcp)
```

## Synthesis Module

The crown of TimeArk. Receives a layer stack + focus, runs ChronoShakti as the master filter, and returns a unified temporal view.

```python
# Example MCP tool call
timeark.synthesize(
    layers=["chronoshakti", "vedic", "hebrew", "hoyoverse"],
    focus="today",
    location="Melbourne",
    output="calendar_overlay"
)
```

ChronoShakti is always active in synthesis — poison time and danger time override all other layer priorities.

## ChronoShakti Doctrine

ChronoShakti is the master awareness filter. Its awareness hierarchy:

1. **Poison time** (Rahu Kaal, Yamagandam, Gulika) — avoid initiating new work, travel, important decisions
2. **Danger time** — reduced capacity windows
3. **North Node of the Moon (Rahu)** — current collective shadow theme
4. **Planetary hora** — ruling planet of the current hour, governs which activity types are favoured
5. **Day lord** — governing planet of the day
6. **Nakshatra** — lunar mansion, somatic/energetic quality
7. **Tithi** — lunar day, ceremonial quality

## Build Order

1. `chronoshakti` — seed from existing `FORGE/TimeArk/scripts/hora_ephemeris.py`
2. `hoyoverse` — HoYoverse API integration (immediate: game event calendar need)
3. `vedic` — full Vedic stack (pyswisseph + astral)
4. `iching` — hexagram engine
5. `shrine` — Shrine of Astra daily draw
6. `synthesis` — layer compositor
7. `notifications` + `telegram` — delivery layer
8. `google_cal` + `thunderbird` + `webcal` — external calendar sync

## Constraints for Agents

- Load this skill before any work in `CORE/TimeArk/`
- Document every new MCP tool in this skill before closing the session
- Never hardcode lat/lon/tz — read from `config.toml`
- Never hardcode API keys — reference paths in `NEXUS/`
- Data writes → `CORE/TimeArk/data/` (not ROOTS)
- Divination log outputs → `LOGS/divinations/TimeArk/` via the `outputs/` symlink
- Install packages through Lane 2 (`helmcortex-anaconda`) only
- Do not commit to git without explicit instruction from Mètsàtron

