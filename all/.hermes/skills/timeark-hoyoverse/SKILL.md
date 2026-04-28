---
name: timeark-hoyoverse
description: HoYoverse and Kuro Games modules — game events, banners, weekly bosses. Load `/timeark` first for general server context.
---

*description: HoYoverse and Kuro Games modules — game events, banners, weekly bosses. Load `/timeark` first for general server context.*

> **Model:** `gpt-5.4` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# Skill: timeark-hoyoverse

> *Load for any work on the `hoyoverse` or `kurogames` modules. Load `/timeark` first for general server context.*

## Why This Module Exists

Game event calendars across four live-service games (Genshin Impact, Honkai: Star Rail, Zenless Zone Zero, Wuthering Waves) have overlapping events, rotating weekly bosses, limited-time banners, and resin-gated content with real consequences for missing reset windows. The PixelCortex harness now connects to HoYoverse API — TimeArk provides the temporal intelligence layer that makes that data actionable.

## Supported Games

| Module | Game | Developer | API Source |
|--------|------|-----------|------------|
| `hoyoverse` | Genshin Impact | HoYoverse | HoYoLAB API |
| `hoyoverse` | Honkai: Star Rail | HoYoverse | HoYoLAB API |
| `hoyoverse` | Zenless Zone Zero | HoYoverse | HoYoLAB API |
| `kurogames` | Wuthering Waves | Kuro Games | Kuro API |

## MCP Tools to Implement

| Tool | Description |
|------|-------------|
| `hoyoverse_events_today` | All active events across HoYo games right now |
| `hoyoverse_events_week` | This week's events — what starts/ends when |
| `hoyoverse_banners_active` | Current character/weapon banners + days remaining |
| `hoyoverse_weekly_bosses` | Weekly boss rotation + current weaknesses |
| `hoyoverse_reset_schedule` | Daily/weekly reset times for all games |
| `hoyoverse_deadline_urgent` | Events/banners ending within 48h — action required |
| `kurogames_events_today` | Wuthering Waves active events |
| `kurogames_banners_active` | WuWa current banners |

## Data Storage

```
CORE/TimeArk/data/games/
├── GenshinImpact/
│   ├── events.json
│   ├── banners.json
│   └── bosses.json
├── HonkaiStarRail/
│   ├── events.json
│   ├── banners.json
│   └── bosses.json
├── ZenlessZoneZero/
│   ├── events.json
│   └── banners.json
└── WutheringWaves/
    ├── events.json
    └── banners.json
```

JSON files are refreshed on a schedule (configurable in `config.toml`) or on-demand tool call. Do not hardcode event data — always fetch from API or use cached JSON with a TTL.

## API Configuration

Keys referenced via config:

```toml
[keys]
hoyoverse_ltuid = "NEXUS/keys/hoyoverse_ltuid"
hoyoverse_ltoken = "NEXUS/keys/hoyoverse_ltoken"
hoyoverse_cookie_token = "NEXUS/keys/hoyoverse_cookie_token"
```

HoYoLAB cookie-based auth: `ltuid` + `ltoken` + `cookie_token`. These are user-specific session tokens from the HoYoLAB browser session.

## Integration with ChronoShakti

When returning event urgency, apply ChronoShakti filter:
- If deadline is during a poison time window, flag prominently
- If current hora favours gaming activity, surface high-priority events
- Include hora context in deadline alerts

## Output Schema (hoyoverse_deadline_urgent)

```json
{
  "as_of": "2026-04-25T13:00:00+10:00",
  "urgent_items": [
    {
      "game": "Genshin Impact",
      "type": "banner",
      "name": "Furina",
      "ends_in": "23h 14m",
      "ends_at": "2026-04-26T12:00:00+10:00",
      "action": "Pull now if planned",
      "chronoshakti_note": "Rahu Kaal at 15:00-16:30 today — avoid pulling during that window"
    }
  ]
}
```

## Dependencies

```
aiohttp >= 3.9
pydantic >= 2.0
fastmcp
```

