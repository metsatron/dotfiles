---
name: nexus-update
description: nexus-update - Refresh Local NEXUS Mirrors
---

# nexus-update - Refresh Local NEXUS Mirrors

Use this when the user wants the local NEXUS skill and agent source repos refreshed before auditing or borrowing from them.

## Steps

1. Resolve the local NEXUS root, preferring `~/HelmCortex/NEXUS/git`.
2. Update the repos that exist there, such as:
   - `awesome-claude-skills`
   - `claude-forge`
   - `everything-claude-code`
   - `Obsidian-CLI-skill`
   - `obsidian-skills`
   - `skills`
3. For each present repo, run:

```bash
git pull --recurse-submodules
git submodule update --remote --merge
```

4. Report which repos updated, which were already current, and any failures.

## Rules

- skip missing repos instead of inventing them
- treat NEXUS repos as source mirrors, not active OpenCode features by default
- use this before `skill-sync` when the user wants the latest upstream overlays compared
