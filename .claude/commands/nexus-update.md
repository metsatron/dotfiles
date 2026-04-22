Pull latest changes for all NEXUS skill/agent repos.

```bash
NEXUS="/home/metsatron/mnt/x230/HelmCortex/NEXUS/git"
for repo in awesome-claude-skills claude-forge everything-claude-code \
            Obsidian-CLI-skill obsidian-skills skills; do
  echo "=== $repo ==="
  git -C "$NEXUS/$repo" pull --recurse-submodules 2>&1 | tail -3
  git -C "$NEXUS/$repo" submodule update --remote --merge 2>&1 | tail -3
done
```

Report: repos updated, any failures. If spawning subagents for per-repo analysis, use model: claude-haiku-4-5.
