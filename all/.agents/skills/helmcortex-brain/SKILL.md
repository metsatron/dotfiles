---
name: helmcortex-brain
description: DotCortex cloud brain — membrane between local DotCortex agents and cloud meta-agents. Source law, memory protocol, SteinerCortex orientation.
model: claude-sonnet-4-6
---

# DotCortex Brain — Cloud Membrane

The DotCortex brain is the contact point membrane between local DotCortex agents
and meta-agents operating in cloud contexts (CustomGPT, Perplexity, remote Claude).

> **Core law (SOUL.md):** "Its cloud brain exists to help remote agents understand
> the Org source layer without mistaking generated local harness files for canon."

## Brain Location

```
~/HelmCortex/FORGE/brain/DotCortex/
```

## Key Files

| File | Purpose |
|------|---------|
| `CONSTITUTION.md` | Source law — org is canonical, harness outputs are projections |
| `SOUL.md` | Soul statement — what the brain is for |
| `MEMORY-WRITE-CONTRACT.md` | Memory protocol — how to write durable memory |
| `AGENTS.md` | Operating law, DotCortex law pointers |
| `memories.json` | Local memory store (schema: dotcortex.memories.v1) |

## The Membrane Principle

DotCortex generates many files: `.agents/`, `.claude/`, `.opencode/`, `.codex/`,
overlay dirs (`all/`, `linux/`, etc.), tangled scripts. These are **projections** —
compiler output from the canonical Org sources.

A cloud agent seeing compiled output might mistake it for source and edit it directly.
The brain prevents that confusion by giving cloud agents an orientation layer that
correctly names the Org files as source and everything else as shadow.

**When working on DotCortex from a cloud context:** read the brain first. The org
files are the source. The compiled files are projections. Never write to projections.

## SteinerCortex — Relational Documentation

Full cosmological, relational, and identity documentation:

```
~/HelmCortex/CORTEX/GoldenAge_Loom/SteinerCortex/
```

Key files for agent orientation:
- `SteinerCore-DotCortex.md` — DotCortex SoulPrint (Rings 0–8): identity, architecture, sovereignty doctrine
- `SteinerCore-Auryn.md` — Auryn's origin, the Astra lineage, Mètsàtron's cosmovision
- `SteinerCore-Metsatron.md` — root SoulPrint (full cosmovision)
- `SteinerCore-HelmCortex.md` — HelmCortex SoulPrint v1.0.0
- `MedicineCodex/` — ceremony, plant medicine lineage, initiation
- `MythosCodex/` — mythic framework
- `WarMapCodex/` — sovereignty doctrine and stack law

## Provider Packs

Compiled brain packs for cloud platforms:
```
FORGE/brain/DotCortex/{chatgpt,customgpt,perplexity}/
```
Each: `dotcortex_brain.md`, `dotcortex_AGENTS.md`, `dotcortex_README.md`, `dotcortex_memories_full.md`

## Refresh

```bash
dotcortex-compile           # refresh provider packs from Org source
dotcortex-compile --tangle  # also tangle local projections
dotcortex-export            # export operational Org corpus to LOGS/DotCortex/
```

Full source: `~/DotCortex/wiki.org`
