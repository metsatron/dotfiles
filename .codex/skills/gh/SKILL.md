---
name: gh
description: GitHub CLI for repository operations, pull requests, issues, releases, and API queries.
---

# GitHub CLI

Use this skill when you need GitHub repo operations, PR management, issue tracking, release checks, or raw API access.

## Core Commands

```bash
# Repo status
gh repo view
gh repo view <owner/repo>
gh repo list <owner>

# Issues
gh issue list
gh issue list --state closed
gh issue list --label bug
gh issue create --title "..." --body "..."
gh issue view <number>
gh issue close <number>
gh issue comment <number> --body "..."

# Pull Requests
gh pr list
gh pr status
gh pr view <number>
gh pr create --title "..." --body "..."
gh pr checkout <number>
gh pr checks <number>
gh pr diff <number>
gh pr merge <number>
gh pr close <number>

# Releases
gh release list
gh release view <tag>
gh release create <tag> --title "..." --notes "..."
gh release download <tag>

# Search
gh search repos <query>
gh search issues <query>
gh search prs <query>

# API (raw)
gh api repos/<owner>/<repo>
gh api repos/<owner>/<repo>/pulls/<number>/comments
```

## NEXUS Repo Operations

Check for updates across NEXUS source repos:

```bash
NEXUS="/home/metsatron/mnt/x230/HelmCortex/NEXUS/git"

gh release list --repo kepano/obsidian-skills --limit 5
gh release list --repo anthropics/skills --limit 5
gh release list --repo sangrokjung/claude-forge --limit 5

gh api repos/kepano/obsidian-skills/commits --jq '.[0:3] | .[].commit.message'

git -C "$NEXUS/<repo>" log HEAD..origin/main --oneline
```

## Flags Reference

```
--json <fields>       Output as JSON with specific fields
--jq <expression>     Filter JSON output
--limit <n>           Limit results
--state <state>       Filter: open, closed, merged, all
--label <label>       Filter by label
--assignee <user>     Filter by assignee
--repo <owner/repo>   Target specific repo (default: current dir)
```
