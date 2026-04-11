---
name: defuddle
description: Extract clean markdown from web pages using Defuddle CLI, removing clutter, navigation, and ads. Prefer over raw page capture for standard articles, docs, and blog posts to reduce token usage.
---

# Defuddle

Use Defuddle CLI to extract clean readable content from web pages. Prefer it over raw HTML capture for standard web pages because it removes navigation, ads, and clutter.

## Use This Skill For

- extracting article or documentation content from URLs
- converting web pages to clean markdown for analysis or note taking
- reducing token load when full raw HTML is unnecessary

Do not use it for pages that require JavaScript rendering or authentication. A browser-based fetch may handle those better.

## Prerequisites

If not installed: `npm install -g defuddle`

## Usage

Always use `--md` for markdown output:

```bash
defuddle parse <url> --md
```

Save to file:

```bash
defuddle parse <url> --md -o content.md
```

Extract specific metadata:

```bash
defuddle parse <url> -p title
defuddle parse <url> -p description
defuddle parse <url> -p domain
```

## Output Formats

| Flag | Format |
|------|--------|
| `--md` | Markdown |
| `--json` | JSON with both HTML and markdown |
| (none) | HTML |
| `-p <name>` | Specific metadata property |

## Canonical Reference

- upstream source: `NEXUS/git/obsidian-skills/skills/defuddle/SKILL.md`
