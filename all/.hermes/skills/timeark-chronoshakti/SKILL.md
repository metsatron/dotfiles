---
name: timeark-chronoshakti
description: ChronoShakti module — hora engine, poison time, danger windows, North Node. Load `/timeark` first for general server context.
---

*description: ChronoShakti module — hora engine, poison time, danger windows, North Node. Load `/timeark` first for general server context.*

> **Model:** `gpt-5.4` | **Effort:** `high` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# Skill: timeark-chronoshakti

> *Load for any work on the `chronoshakti` module specifically. Load `/timeark` first for general server context.*

## What ChronoShakti Is

ChronoShakti is the master temporal awareness engine. It is the first module built and the filter through which all other TimeArk modules are interpreted. It answers: **what time is it, really?**

Hora (planetary hour) awareness is the primary mechanism. Combined with poison time detection, North Node awareness, and Vedic day quality, it produces a moment-by-moment sacred time signature.

## Source File

Existing implementation: `FORGE/TimeArk/scripts/hora_ephemeris.py`

This file precomputes all planetary hours for a given year, timezone, and location into a JSON file at `ROOTS/TimeArk/index/hora/YYYY-TZ_SAFE.json`. The MCP migration wraps this engine as on-demand queryable tools.

**Migration path:**
- Copy `hora_ephemeris.py` → `CORE/TimeArk/modules/chronoshakti/engine.py`
- Strip CLI argument parsing into a separate `cli.py`
- `engine.py` exposes pure functions: `get_hora(dt, lat, lon, tz)`, `get_day_quality(dt, lat, lon, tz)`, etc.
- `tools.py` wraps these as `@mcp.tool()` decorated functions

## MCP Tools to Implement

| Tool | Description | Inputs |
|------|-------------|--------|
| `chronoshakti_now` | Full ChronoShakti reading for current moment | location (optional, uses config default) |
| `chronoshakti_at` | Reading for a specific datetime | datetime, location |
| `hora_today` | All planetary hours for today | location (optional) |
| `hora_week` | Hora table for current week | location (optional) |
| `poison_time_today` | All Rahu Kaal, Yamagandam, Gulika windows today | location (optional) |
| `is_poison_time` | Boolean — is right now a poison time window? | location (optional) |
| `day_quality` | Day lord, nakshatra, tithi for a date | date, location |
| `north_node_theme` | Current Rahu/Ketu axis sign + collective shadow theme | — |

## Output Schema (chronoshakti_now)

```json
{
  "datetime": "2026-04-25T13:00:00+10:00",
  "location": "Melbourne",
  "hora": {
    "planet": "Jupiter",
    "glyph": "♃",
    "start": "12:47",
    "end": "13:51",
    "quality": "Expansion, wisdom, generosity — favoured for learning, planning, teaching"
  },
  "day_lord": "Saturn",
  "poison_time": {
    "active": false,
    "next_window": {"type": "Rahu Kaal", "start": "15:00", "end": "16:30"}
  },
  "danger_time": {"active": false},
  "nakshatra": "Uttara Phalguni",
  "tithi": "Navami (9th lunar day)",
  "north_node": {"sign": "Aries", "theme": "Courage, initiation, raw individual will"},
  "synthesis": "Jupiter hora on Saturn's day — good for structured learning. No poison time active. Proceed."
}
```

## Precomputed Data

The existing `hora_ephemeris.py` writes to `ROOTS/TimeArk/index/hora/YYYY-TZ_SAFE.json`. After migration:
- Precomputed JSONs move to `CORE/TimeArk/data/hora/`
- The engine can serve from precomputed data OR calculate on-demand
- On-demand calculation is preferred for accuracy; precomputed is the fallback cache

## Dependencies

```
astral >= 3.2
pyswisseph >= 2.10
pytz
pydantic >= 2.0
fastmcp
```

All installed in `CORE/anaconda3/` Lane 2.

## Poison Time Reference

| Window | Calculation method | Effect |
|--------|--------------------|--------|
| **Rahu Kaal** | 1/8 of daylight, day-specific slot | Avoid new initiations, travel, decisions |
| **Yamagandam** | 1/8 of daylight, day-specific slot | Avoid auspicious ceremonies |
| **Gulika Kaal** | 1/8 of daylight, day-specific slot | Generally inauspicious |

Day order for Rahu Kaal (from sunrise): Sun=eve, Mon=morn, Tue=aft, Wed=mid, Thu=aft, Fri=morn, Sat=morn

