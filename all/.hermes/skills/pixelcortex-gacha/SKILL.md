---
name: pixelcortex-gacha
description: Manage gacha game tracking in PixelCortex — account details, character rosters, pull history, and spend records.
---

*description: Manage gacha game tracking in PixelCortex — account details, character rosters, pull history, and spend records.*

> **Model:** `gpt-5.4` | **Effort:** `medium` | **Delegate:** `standard`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# PixelCortex Gacha

Use this skill when managing gacha / live-service game data in PixelCortex.

## Structure

```
gacha/
├── accounts.md          — account-level overview (server, AR, summary)
├── GenshinImpact/
│   ├── characters.md    — roster summary
│   └── characters/      — per-character detail files
└── README.md
```

## Schema (meta/gacha_schema.md)

If the schema file is empty, use this structure for account entries:

```yaml
---
game: Game Name
server: server-region
uid: "UID number"
status: active | inactive | retired
last_updated: YYYY-MM-DD
tags: [gacha, live-service, game-name]
---
```

## Rules

- **Never surface raw credentials** — login tokens, passwords, and payment details stay out of PixelCortex.
- UID numbers are identifiers, not secrets — they may be recorded.
- Spend records are sensitive — include only with Mètsàtron's approval.
- Per-character files use the character's full name as slug: `characters/raiden-shogun.md`.
- Keep `accounts.md` as a high-level overview. Detailed data lives in per-game subdirectories.
- When a gacha game is retired, update `status: retired` and freeze the record — do not delete.

## PixelForge Integration

- `FORGE/PixelForge/scripts/genshin-export.py` — export Genshin Impact account data for import into `gacha/GenshinImpact/`. Run from FORGE, not from PixelCortex.

