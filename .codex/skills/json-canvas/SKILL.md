---
name: json-canvas
description: Create and edit JSON Canvas `.canvas` files with nodes, edges, groups, labels, and valid graph references.
---

# JSON Canvas

Use this skill when the task is about Obsidian Canvas files, JSON Canvas structure, or visual maps stored as `.canvas` documents.

## Use This Skill For

- creating a new canvas file
- adding or editing nodes, groups, and edges
- fixing invalid JSON or dangling edge references
- laying out research maps, flowcharts, mind maps, or project canvases

## File Structure

```json
{
  "nodes": [],
  "edges": []
}
```

## Workflow

1. Parse the existing JSON before editing.
2. Generate unique lowercase 16-character hex ids for nodes and edges.
3. Add or update nodes with required geometry fields.
4. Add edges only after both endpoint node ids exist.
5. Re-validate JSON and graph references before finishing.

## Core Node Types

- `text` - Markdown text inside the node
- `file` - preview of a vault file or attachment
- `link` - external URL
- `group` - visual container for related nodes

## Edge Rules

- `fromNode` and `toNode` must reference existing node ids
- `fromSide` and `toSide` must be one of `top`, `right`, `bottom`, or `left`
- `fromEnd` and `toEnd` must be `none` or `arrow`
- keep ids unique across both `nodes` and `edges`

## Layout Rules

- leave 50-100 pixels between nodes
- align to a loose grid for cleaner canvases
- keep grouped nodes inside the group bounds with some padding
- use `\n` for line breaks in JSON strings, not literal newlines

## Canonical Reference

- full examples: `references/EXAMPLES.md`
- upstream source: `NEXUS/git/obsidian-skills/skills/json-canvas/`
