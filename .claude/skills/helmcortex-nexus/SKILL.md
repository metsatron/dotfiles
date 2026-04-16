---
name: helmcortex-nexus
description: Inspect and refresh HelmCortex NEXUS/git mirrors.
model: claude-haiku-4-5-20251001
---

# HelmCortex NEXUS

Use this skill when you need to inspect, refresh, or compare repositories under HelmCortex's local NEXUS/git mirror.

## Use This Skill For

- checking upstream release activity for mirrored repos
- comparing local NEXUS mirrors against their remotes
- refreshing the local mirror set before audit or comparison work
- browsing curated NEXUS indexes when deciding what to use

## Canonical Paths

- Local mirror root: `/home/metsatron/mnt/x230/HelmCortex/NEXUS/git/`
- Update path: use the local mirror refresh helper or the relevant repo fetch/update flow before comparison

## Workflow

1. Refresh the local mirror or target checkout.
2. Inspect recent commits or release tags.
3. Compare local state against upstream.
4. Keep the summary short and action-oriented.

## Notes

- Prefer `gh` for GitHub-side inspection when available.
- Keep this skill focused on HelmCortex NEXUS inventory and refresh work.
