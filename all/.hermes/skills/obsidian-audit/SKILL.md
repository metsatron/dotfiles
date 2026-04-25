---
name: obsidian-audit
description: Audit Obsidian vault stability, plugin surface, indexing pressure, and persistent follow-up artifacts in MetaCortex and TODO.
---

*description: Audit Obsidian vault stability, plugin surface, indexing pressure, and persistent follow-up artifacts in MetaCortex and TODO.*

> **Model:** `gpt-5.4` | **Effort:** `high` | **Delegate:** `claude-sonnet`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# Obsidian Audit

Use this skill when the user wants a structured audit of an Obsidian vault, plugin set, runtime stability, or a documented handoff for future debugging.

Load `obsidian-cli` alongside this skill when the running app is part of the audit.

## Use This Skill For

- auditing freeze, hang, or slowdown reports in a real vault
- comparing enabled plugins against vault scale and current workspace state
- checking whether dot-directories are being indexed or skipped
- recording findings, next steps, and caveats into MetaCortex and `LOGS/TODO/`
- preserving a session before compaction or closeout

## Audit Workflow

1. Record the current enabled plugin set and whether the session is a clean launch or a post-disable/post-restart state.
2. Measure the vault surface from two angles:
   - filesystem counts and large-note hotspots
   - Obsidian internal counts such as metadata cache size
3. Distinguish visible UI load from retained renderer state. A small visible DOM with huge Chrome node counts suggests detached or retained trees.
4. Separate core Obsidian indexing pressure from plugin pressure.
5. Persist the result into:
   - `CORTEX/GoldenAge_Loom/MetaCortex/Audits/`
   - `CORTEX/GoldenAge_Loom/MetaCortex/Investigations/`
   - `CORTEX/GoldenAge_Loom/MetaCortex/Debugging/`
   - `LOGS/TODO/HelmCortex.md`

## Core Questions

- Is the vault still indexing or has it settled?
- Are dot-directories excluded in practice?
- Is the renderer heap dominated by visible UI or retained detached state?
- Does the current workspace contain stale leaves from disabled plugins?
- Which plugins remain enabled in the baseline that reproduces the issue?

## Durable Findings To Capture

- exact enabled plugin list
- Obsidian version and packaging surface if relevant, especially Flatpak vs `.deb`
- metadata-cache counts
- large visible notes or dashboards
- retained DOM / event-listener / heap counters when available
- whether `obsidian restart` behaves differently from a full manual quit + relaunch
- next-step bisect order

## Rules

- do not treat a post-disable session as a clean baseline
- keep dot-directory assumptions evidence-backed, not inferred from raw filesystem counts
- if the findings change after later manual restarts or concurrent vault work, append that caveat to the audit note instead of rewriting history
- always leave a compact follow-up trail in `LOGS/TODO/HelmCortex.md`

## Canonical Note Targets

- `CORTEX/GoldenAge_Loom/MetaCortex/Audits/obsidian-vault-runtime-audit.md`
- `CORTEX/GoldenAge_Loom/MetaCortex/Investigations/obsidian-freeze-investigation.md`
- `CORTEX/GoldenAge_Loom/MetaCortex/Debugging/obsidian-flatpak-cdp-debugging.md`

