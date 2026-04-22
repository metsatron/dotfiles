---
name: obsidian-bases
description: Create and edit Obsidian Bases `.base` files with filters, formulas, views, properties, and summaries.
---

# Obsidian Bases

Use this skill when the task is about `.base` files, Base views, formulas, filters, or database-like note views in Obsidian.

## Use This Skill For

- creating new `.base` files
- fixing YAML structure inside a Base
- designing filters, formulas, summaries, and view layouts
- debugging why a Base does not render or returns the wrong notes

Do not load it for plain note editing or live CLI actions. Use `obsidian-markdown` or `obsidian-cli` instead.

## Workflow

1. Create valid YAML in a `.base` file.
2. Define global `filters` first.
3. Add `formulas` only when computed values are needed.
4. Define `properties` display names when the output should be human-readable.
5. Add one or more `views` with `order`, optional per-view filters, and summaries.
6. Validate YAML quoting and formula references before finishing.

## Skeleton

```yaml
filters:
  and: []

formulas:
  status_icon: 'if(done, "done", "open")'

properties:
  formula.status_icon:
    displayName: Status

views:
  - type: table
    name: Tasks
    order:
      - file.name
      - formula.status_icon
```

## Common Patterns

```yaml
filters:
  and:
    - file.hasTag("task")
    - 'status != "done"'

formulas:
  days_until_due: 'if(due, (date(due) - today()).days, "")'

views:
  - type: table
    name: Active Tasks
    order:
      - file.name
      - due
      - formula.days_until_due
```

## Critical Rules

- quote formulas carefully; single quotes around formulas with inner double quotes are safest
- date subtraction returns a Duration type — use `.days`, `.hours`, etc. to get a number
- every `formula.X` used in `order`, `properties`, or summaries must exist in `formulas`
- strings containing YAML-special characters must be quoted
- validate final YAML, because minor quoting mistakes break the whole Base

## Canonical Reference

- full functions reference: `references/FUNCTIONS_REFERENCE.md`
- upstream source: `NEXUS/git/obsidian-skills/skills/obsidian-bases/`
