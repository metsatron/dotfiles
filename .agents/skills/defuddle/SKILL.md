---
name: defuddle
description: Extract clean markdown from web pages using Defuddle CLI.
---

# Defuddle

Use Defuddle CLI to extract clean readable content from web pages. Prefer over WebFetch for standard web pages — it removes navigation, ads, and clutter, reducing token usage significantly.

## Use This Skill For

- extracting article or documentation content from URLs
- converting web pages to clean markdown for vault ingestion or analysis
- reducing token load when the full raw HTML from WebFetch is unnecessary

Do not use for pages that require JavaScript rendering or authentication. WebFetch may handle those better.

Note: for browser-based capture into Obsidian, the WebClipper in FireDragon is the primary pipeline. Defuddle is the CLI-side complement for headless or automated extraction.

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
| `--md` | Markdown (preferred) |
| `--json` | JSON with both HTML and markdown |
| (none) | HTML |
| `-p <name>` | Specific metadata property |

## Canonical Reference

- upstream source: `NEXUS/git/obsidian-skills/skills/defuddle/SKILL.md`
