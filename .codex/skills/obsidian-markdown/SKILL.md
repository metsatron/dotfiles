---
name: obsidian-markdown
description: Create and edit Obsidian Flavored Markdown with wikilinks, embeds, callouts, properties, comments, tags, math, and other note-specific syntax.
---

# Obsidian Markdown

Use this skill when the task is about authoring or repairing `.md` files for Obsidian itself, especially when links, callouts, frontmatter, tags, embeds, or note-local syntax matter.

## Use This Skill For

- creating or editing notes that rely on wikilinks, embeds, callouts, or properties
- fixing broken frontmatter or invalid Obsidian-specific Markdown syntax
- converting plain Markdown into Obsidian-friendly notes
- preserving internal note links, block ids, callouts, and hidden comments during edits

Do not load it for live vault actions through the running app. Use `obsidian-cli` for that.

## Workflow

1. Start with valid frontmatter when the note needs properties.
2. Use standard Markdown for structure.
3. Use `[[wikilinks]]` for internal notes and Markdown links only for external URLs.
4. Add embeds and callouts only when they improve navigation or readability.
5. Re-read the final note and make sure YAML, links, and block ids still parse cleanly.

## Core Syntax

```markdown
---
title: Project Alpha
tags:
  - project
  - active
aliases:
  - Alpha
---

[[Note Name]]
[[Note Name|Display Text]]
[[Note Name#Heading]]
[[Note Name#^block-id]]
![[Note Name]]
![[image.png|300]]

> [!note]
> Callout body.

%% hidden comment %%
==highlight==
```

## Formatting Rules

- keep frontmatter as valid YAML
- prefer wikilinks for vault-internal references because Obsidian tracks renames
- keep block ids attached to the exact paragraph or block they identify
- preserve callout markers like `> [!warning]` exactly
- inline tags use `#tag` or `#nested/tag`
- embeds use `![[...]]`

## Common Patterns

```markdown
This project connects to [[Architecture Notes#Routing]].

> [!warning] Migration Risk
> Update backlinks before renaming the folder.

![[Architecture Diagram.png|600]]

Text with a footnote.[^1]
[^1]: Footnote content.
```

## Canonical References

- properties: `references/PROPERTIES.md`
- embeds: `references/EMBEDS.md`
- callouts: `references/CALLOUTS.md`
- upstream source: `NEXUS/git/Obsidian-CLI-skill/skills/obsidian-markdown/`
