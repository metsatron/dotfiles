---
name: gh
description: GitHub CLI for repo operations, PR management, issue tracking, checking NEXUS repos for updates and releases.
model: claude-haiku-4-5-20251001
---

# GitHub CLI (gh)

## Core Commands

```bash
# Repo status
gh repo view                          # view current repo info
gh repo view <owner/repo>             # view specific repo
gh repo list <owner>                  # list repos for user/org

# Issues
gh issue list                         # list open issues
gh issue list --state closed          # list closed issues
gh issue list --label bug             # filter by label
gh issue create --title "..." --body "..."
gh issue view <number>
gh issue close <number>
gh issue comment <number> --body "..."

# Pull Requests
gh pr list                            # list open PRs
gh pr status                          # show status of relevant PRs
gh pr view <number>
gh pr create --title "..." --body "..."
gh pr checkout <number>
gh pr checks <number>                 # show CI status
gh pr diff <number>
gh pr merge <number>
gh pr close <number>

# Releases
gh release list                       # list releases
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

# Check if a repo has new releases
gh release list --repo kepano/obsidian-skills --limit 5
gh release list --repo anthropics/skills --limit 5
gh release list --repo sangrokjung/claude-forge --limit 5

# Check recent commits
gh api repos/kepano/obsidian-skills/commits --jq '.[0:3] | .[].commit.message'

# Compare local vs remote
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
