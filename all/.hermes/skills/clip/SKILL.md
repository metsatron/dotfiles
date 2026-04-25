---
name: clip
description: File an Obsidian WebClipper capture into the research/TODO system, or scan for orphaned clippings.
---

*description: File an Obsidian WebClipper capture into the research/TODO system, or scan for orphaned clippings.*

> **Model:** `gpt-5.4-mini` | **Effort:** `low` | **Delegate:** `mini`
>
> *If you are a primary agent reading this skill, dispatch to the matching
> subagent tier before executing the skill body.*

# /clip — File a WebClipping

Take an Obsidian WebClipper file and route it into the research/TODO system. Arguments: $ARGUMENTS

## Usage
- `/clip <path>` — file a specific clipping
- `/clip` (no args) — scan `LOGS/WebClipper/` for unlinked clippings and offer to file them

## Steps (with path)

### 1. Read the Clipping
Use `obsidian read path="LOGS/WebClipper/<path>"` to read the file. Extract:
- Title
- URL (from frontmatter or content)
- Key topics/technologies mentioned

### 2. Determine Layer
Based on content, classify as:
- **Dionysus** — if about memory, relationships, AI companionship, personas, soul
- **Hierem** — if about tooling, infrastructure, code, build systems, MCP servers
- **Both** — if cross-cutting

### 3. Find Matching Project
Use `obsidian search query="<project-name or key technology>" limit=15` and filter results under `LOGS/Antigravity/projects/` to find a matching evaluation doc. Also try the GitHub URL hostname as a query term.

### 4. Link the Clipping
If a matching project exists:
- Use `obsidian append path="LOGS/Antigravity/projects/<name>/research/<name>-evaluation.md" content="## WebClippings\n- [[LOGS/WebClipper/<path>|<title>]]"` (or append just the list item if the section already exists)

If no matching project:
- Use `obsidian append path="LOGS/Research/README.md" content="- [[LOGS/WebClipper/<path>|<title>]]"` under the appropriate layer heading
- Or suggest creating a new evaluation scaffold via `/research`

### 5. Confirm
Output what was linked and where. If the clipping doesn't fit anywhere, say so and suggest options.

## Steps (no path — scan mode)

### 1. List All WebClippings
Use `obsidian search query="site:" path="LOGS/WebClipper" limit=50` to enumerate clippings (they all contain URLs). If that returns too few results, try `obsidian search query="tags:" path="LOGS/WebClipper" limit=50` or fall back to `ls LOGS/WebClipper/` via Bash.

### 2. Check Each Against Research System
For each clipping file found, run `obsidian backlinks path="LOGS/WebClipper/<file>"` to see if it is referenced anywhere in the vault.

### 3. Report Orphans
List any clippings with zero backlinks. For each, suggest where it might belong.

## Rules
- Never move or rename WebClipper files — they stay in `LOGS/WebClipper/` where Obsidian put them
- Only add wikilinks — the clipping itself is the source of truth
- Every clipping should have at least one backlink somewhere in the system
- If a clipping is about a GitHub repo relevant to an active evaluation, prioritize linking it there
- Use Obsidian wikilink format: `[[LOGS/WebClipper/path/to/file|Display Title]]`

