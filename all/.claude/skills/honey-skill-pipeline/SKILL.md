---
name: honey-skill-pipeline
description: How skills are authored, compiled and delivered on Honey (DotCortex tangle versus HelmCortex compile and the skills mirror), which lane a new skill belongs in, how to deploy one to this account, and how to read the HelmCortex compile from Honey through kikin. Use when adding or changing a skill, or when asked whether skills come from HelmCortex.
---

# Honey skill pipeline

Use this when asked to add, change, deploy or explain a skill on Honey, or whether skills are
"compiled from HelmCortex". The traced detail and the unverified items are in
`~/DotCortex/agents-skills-honey.org` ("Reference: how skills are compiled and delivered").

## Pick the lane

- **A skill for Honey work** (Honey ops, Aura, DSH, llama-swap): author it in DotCortex. Add a
  `skill-NAME-body` block and a `.claude/skills/<slug>/SKILL.md` tangle block to
  `agents-skills-honey.org` (schema in `agents-skills.org`). Never write SKILL.md directly.
- **A skill about Mètsàtron's userspace or HelmCortex internals**: it belongs in HelmCortex
  (`FORGE/harness/userspace/SKILLS.md` on the hub), not in the public DotCortex repo. Do not
  edit compiled output under `NEXUS/stow/`. Hand the text to Mètsàtron or mail the fleet.

## DotCortex lane, step by step

1. Edit the Org file. `all/.local/bin/org-style-lint` must show nothing for your file.
2. `cd ~/DotCortex && make tangle` emits `all/.claude/skills/<slug>/SKILL.md`.
3. Make it live **on this account**: `ln -s ~/DotCortex/all/.claude/skills/<slug> ~/.claude/skills/<slug>`.
   `loom stow` does NOT deliver it, because `layers.org` has the `honey / gille` row as `planned`
   (not active). It appears in new sessions, not the running one.
4. Commit only when asked, on a `land/<topic>-<date>` branch, never push. The commit guard
   refuses a dirty tracked tree; for a deliberate split use `DOTCORTEX_GUARD_ALLOW_DIRTY=1`
   once, and check each commit's file list afterwards.

## Reading the HelmCortex side from Honey (read-only, through kikin)

- `ssh kikin 'helmcortex-compile --list-scopes'` lists scopes.
- `ssh kikin 'helmcortex-compile --scope <scope> --type skills --dry-run'` prints every target
  path and body and writes nothing. Name files; a broad `grep -r` over `~/HelmCortex` hangs on NFS.
- `helmcortex-compile` is routed as class `hub`; `local-apply` is the caller-local mode.
- Do NOT run a real `canonical` compile, `helmstow` or `helmstow --to honey` from Honey without
  Mètsàtron's word. They write hub output, his home, or the bots' skills, and `--adopt` is his alone.

## What Honey does not have (checked 2026-11-10)

This account (`gille`) has no `hx-router`, no fleet-router registry, no `x230-helmcortex-git`
alias, no skills mirror, no cron line, no `helmcortex-skills-sync` on PATH; `~/HelmCortex` is a
stub with only `ROOTS/`. So skills do not arrive from HelmCortex on this account today.
**The Honey bots' account (`agent-claude`) does get them**: the hub runs `helmstow --to honey`
(allowlist `FORGE/scripts/helmstow_remote/profiles/honey.toml`, root-owned copy in
`/usr/local/share/helmcortex/stow`, stowed as the bot). Nothing projects automatically.
Read-only checks from here: `ssh kikin 'helmstow --to honey --verify'` and `--dry-run`. On
2026-11-10 `--verify` showed 5 of 18 skills drifted from the hub; the sync itself is
Mètsàtron's call. Getting this account a profile of its own needs his word. Say so rather than
claiming a skill is compiled from HelmCortex.
Existing skills: `honey-host` is a hand-placed file, `llm-benchmark` comes from the
`llm-report-bench` repo, `inbox` is a copy of a DotCortex skill.
