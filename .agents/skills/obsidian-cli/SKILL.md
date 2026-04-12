---
name: obsidian-cli
description: Use the official Obsidian CLI against a live vault.
---

# Obsidian CLI

Use this skill when the task needs the running Obsidian app, live vault state, or the official `obsidian` CLI rather than plain filesystem edits.

## Trigger Conditions

Load this skill when any of these are true:

- the user wants to read, create, append, prepend, move, rename, or delete notes through Obsidian
- the user asks to work with daily notes, tasks, tags, backlinks, sync history, Bases, or file history
- the task involves plugin or theme development and needs `obsidian eval`, screenshots, console logs, CSS inspection, or DOM inspection
- the user is asking for vault automation or shell workflows built around the official CLI

Do not load it for pure Markdown authoring, `.base` editing, `.canvas` editing, or GUI-only explanation. Use the format skills for file syntax work.

## HelmCortex Use

- prefer direct file edits when the task is just editing repo files that happen to contain Obsidian content
- prefer `obsidian` when the user wants actions against the live vault or app state
- keep paths vault-relative, not absolute filesystem paths
- read `references/command-reference.md` when you need full flags or subcommand details

## Prerequisites

- Obsidian Desktop `v1.12+`
- CLI enabled in Settings -> Command line interface
- Obsidian running, because the CLI talks to the app over IPC

Linux: the `.deb` package is safer than Snap for IPC. Headless use needs `xvfb` and a valid `DISPLAY`.

## Syntax

Parameters use `key=value`. Quote values with spaces.

```bash
obsidian <command> [key=value ...] [flags]
```

Target a specific vault by making it the first argument:

```bash
obsidian "My Vault" daily:read
obsidian "My Vault" search query="meeting notes"
```

## Core Patterns

```bash
obsidian read path="folder/note.md"
obsidian create path="folder/note" content="# New Note"
obsidian append path="folder/note.md" content="New paragraph"
obsidian daily:append content="- [ ] Review pull requests"
obsidian search query="project alpha" limit=10
obsidian property:set path="note.md" name="status" value="active"
obsidian tasks daily
obsidian backlinks path="note.md"
obsidian orphans
obsidian unresolved
```

## Developer Loop

```bash
obsidian plugin:reload id="my-plugin"
obsidian dev:errors
obsidian dev:console limit=20
obsidian dev:screenshot path="debug/screenshot.png"
obsidian dev:dom selector=".workspace-leaf" text
obsidian eval code="app.vault.getFiles().length"
```

## Operational Notes

- `create` adds `.md` automatically when the target is a note path without the extension
- `move` expects the full destination path, including `.md`
- `template:insert` targets the active editor and does not accept `path=`
- `property:set` stores list-like values as strings; edit frontmatter directly for real YAML arrays
- `eval` is safest as single-line JavaScript unless you write the script to a temp file first
- multi-vault targeting can fail on some installs; if it does, switch vaults in Obsidian and omit the vault name

## Canonical Reference

- full command reference: `references/command-reference.md`
- upstream source: `NEXUS/git/Obsidian-CLI-skill/skills/obsidian-cli/`
