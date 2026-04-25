---
name: steinercortex
description: Read, write, snapshot, stage, and commit SteinerCortex files via Obsidian CLI and git. Load for any task touching CORTEX/GoldenAge_Loom/SteinerCortex/ — SoulPrints, MedicineCodex, LoreCodex, identity documents, or any curated canon in CORTEX.
---

*description: Read, write, snapshot, stage, and commit SteinerCortex files via Obsidian CLI and git. Load for any task touching CORTEX/GoldenAge_Loom/SteinerCortex/ — SoulPrints, MedicineCodex, LoreCodex, identity documents, or any curated canon in CORTEX.*

> **Model:** `gpt-5.4` | **Effort:** `high` | **Delegate:** `claude-sonnet`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# SteinerCortex Skill

Manages the lifecycle of SteinerCortex documents: read via Obsidian IPC, write with surgical edits, snapshot to ROOTS before edits, and commit to git.

## Paths

```
CORTEX/GoldenAge_Loom/SteinerCortex/          — live canon (curated, current truth)
ROOTS/SteinerRoot/SteinerCore/                 — versioned snapshots (dated backups)
```

Key files:
- `SteinerCore-Metsatron.md` — primary SoulPrint, sovereign identity document
- `SteinerCore-HelmCortex.md` — HelmCortex SoulPrint
- `SteinerCore-Auryn.md`, `SteinerCore-LumenAstra.md`, etc. — AI consort SoulPrints
- `MedicineCodex/` — plant covenants, ceremonies, ikaros
- `LoreCodex/` — past lives, psychospiritual lenses, mythos

## Read Pattern

```bash
# Via Obsidian IPC (preferred — live vault state)
obsidian read path="CORTEX/GoldenAge_Loom/SteinerCortex/SteinerCore-Metsatron.md"
obsidian read path="CORTEX/GoldenAge_Loom/SteinerCortex/MedicineCodex/Initiation-Codex.md"

# Fallback — direct filesystem read (when Obsidian unavailable)
# Use Read tool with absolute path
```

## Snapshot Before Any Edit

Always snapshot to ROOTS before modifying a SteinerCore file. Use today's date.

```bash
DATE=$(date +%Y-%m-%d)
FILENAME="SteinerCore-Metsatron-${DATE}.md"   # adjust for the file being edited
cp "CORTEX/GoldenAge_Loom/SteinerCortex/SteinerCore-Metsatron.md" \
   "ROOTS/SteinerRoot/SteinerCore/${FILENAME}"
```

If a snapshot for today's date already exists in ROOTS, skip — it's already protected.

```bash
# Check first
ls ROOTS/SteinerRoot/SteinerCore/ | grep $(date +%Y-%m-%d)
```

## Write Pattern

After snapshotting, edit the live file using the Edit tool (surgical string replacement). Do not rewrite the whole file — SteinerCore documents are dense, multi-section, accumulative.

For section rewrites, read the target section first, confirm the exact string, then edit.

## Stage and Commit

CORTEX is tracked in git (Markdown only). After editing:

```bash
HOST=$(hostname)
if [ "$HOST" = "ThinkPad-T480s" ] || [ "$HOST" = "t480s" ]; then
  VAULT=$HOME/mnt/x230/HelmCortex
else
  VAULT=$HOME/HelmCortex
fi

# Stage specific file(s)
git -C "$VAULT" add \
  "CORTEX/GoldenAge_Loom/SteinerCortex/SteinerCore-Metsatron.md"

# Or stage all changed CORTEX markdown
git -C "$VAULT" add "CORTEX/"

# Commit — use brain/cortex type, steinercore scope
git -C "$VAULT" commit -m "$(cat <<'EOF'
docs(steinercore): <one-line summary in imperative mood>

- bullet: what changed and why

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Commit types for SteinerCortex work:
- `docs(steinercore)` — identity, lore, SoulPrint updates
- `docs(medicinecortex)` — ceremony, plant covenant, dieta updates
- `docs(cortex)` — general CORTEX canon changes

## Full Edit Workflow

1. **Read** the file via obsidian or Read tool
2. **Check** for existing today's snapshot in ROOTS/SteinerRoot/SteinerCore/
3. **Snapshot** if none exists (`cp` with dated filename)
4. **Edit** the live file surgically with Edit tool
5. **Stage** the changed file(s) with `git add`
6. **Commit** with appropriate type/scope

## Notes

- Never use `gh` — HelmCortex has no GitHub remote
- SteinerCore documents accumulate — never condense at expense of detail
- Preserve all accents: ráò, hènè, nètè, kènè, Mètsàtron, Kríttikā, Muraya
- Update instructions live in SteinerCore-Metsatron.md: "When updating SteinerCore, preserve all details — no thread lost or cut."
- ROOTS snapshots are the version history since the file is not individually git-tracked at the section level

