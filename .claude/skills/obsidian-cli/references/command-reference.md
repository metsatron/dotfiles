# Obsidian CLI — Full Command Reference

Complete reference for all official Obsidian CLI commands (v1.12+).

**Syntax**: `obsidian [vault] <command> [subcommand] [key=value ...] [flags]`

---

## Files

```bash
obsidian read path="folder/note.md"
obsidian create path="folder/note" content="# Title\n\nBody"
obsidian create path="folder/note" template="template-name"
obsidian append path="folder/note.md" content="text"
obsidian prepend path="folder/note.md" content="text"
obsidian move path="old/note.md" to="new/note.md"
obsidian rename path="folder/note.md" name="new-name"
obsidian delete path="folder/note.md"
obsidian delete path="folder/note.md" permanent
obsidian files
obsidian files ext=md
obsidian files folder="subfolder"
obsidian files total
obsidian folders
obsidian file path="folder/note.md"
obsidian random
obsidian random:read
```

Notes:
- `create` path omits `.md` — appended automatically
- `move to=` requires full path including `.md`
- `rename name=` is filename only, no path, no extension
- `prepend` inserts after frontmatter, not at byte 0

---

## Daily Notes

Requires Daily Notes core plugin enabled.

```bash
obsidian daily
obsidian daily:read
obsidian daily:append content="text"
obsidian daily:prepend content="text"
obsidian daily:path
```

---

## Search

```bash
obsidian search query="text"
obsidian search query="text" path="folder"
obsidian search query="text" limit=10
obsidian search query="text" format=json
obsidian search query="text" case
obsidian search:context query="text"
obsidian search:context query="text" path="folder" limit=10
obsidian search:open query="text"
```

`format=json` returns `["folder/note.md", ...]`

---

## Properties

```bash
obsidian properties path="note.md"
obsidian property:read path="note.md" name="status"
obsidian property:set path="note.md" name="status" value="active"
obsidian property:remove path="note.md" name="draft"
obsidian aliases path="note.md"
```

`property:set` stores value as a string — for real YAML arrays, edit frontmatter directly or use `eval`.

---

## Tags

```bash
obsidian tags
obsidian tags counts
obsidian tags counts sort=count
obsidian tags path="note.md"
obsidian tag name="project/alpha"
```

---

## Tasks

```bash
obsidian tasks
obsidian tasks all
obsidian tasks done
obsidian tasks path="note.md"
obsidian tasks daily
obsidian task path="note.md" line=12 toggle
obsidian tasks | grep "\[ \]"    # incomplete only
```

---

## Links

```bash
obsidian backlinks path="note.md"
obsidian backlinks path="note.md" counts
obsidian links path="note.md"
obsidian unresolved
obsidian orphans
obsidian deadends
```

---

## Bookmarks

```bash
obsidian bookmarks
obsidian bookmark file="folder/note.md"
obsidian bookmark file="folder/note.md" subpath="#Heading"
obsidian bookmark folder="projects"
obsidian bookmark search="query" title="My Search"
obsidian bookmark url="https://example.com" title="Link"
```

---

## Templates

```bash
obsidian templates
obsidian template:read name="weekly-review"
obsidian template:read name="weekly-review" resolve title="My Note"
obsidian template:insert name="weekly-review"
```

`template:insert` targets the active editor — no `path=` support. For CLI-driven creation use `create path="..." template="..."`.

---

## Plugins

```bash
obsidian plugins
obsidian plugins:enabled
obsidian plugins versions
obsidian plugins:restrict
obsidian plugins:restrict on|off
obsidian plugin id="dataview"
obsidian plugin:enable id="canvas"
obsidian plugin:disable id="canvas"
obsidian plugin:install id="dataview"
obsidian plugin:uninstall id="dataview"
obsidian plugin:reload id="my-plugin"
```

---

## Sync

Requires active Obsidian Sync subscription.

```bash
obsidian sync
obsidian sync on|off
obsidian sync:status
obsidian sync:history path="note.md"
obsidian sync:read path="note.md" version=3
obsidian sync:restore path="note.md" version=3
obsidian sync:deleted
obsidian sync:open
```

---

## Themes

```bash
obsidian themes
obsidian theme
obsidian theme:set name="Minimal"
obsidian theme:set name=""
obsidian theme:install name="Minimal"
obsidian theme:install name="Minimal" enable
obsidian theme:uninstall name="Minimal"
```

---

## CSS Snippets

```bash
obsidian snippets
obsidian snippets:enabled
obsidian snippet:enable name="my-style"
obsidian snippet:disable name="my-style"
```

---

## Commands & Hotkeys

```bash
obsidian commands
obsidian command id="app:reload"
obsidian hotkeys
obsidian hotkey id="app:open-settings"
obsidian hotkey id="app:open-settings" verbose
```

---

## Obsidian Bases

```bash
obsidian bases
obsidian base:query file="tasks" format=json
obsidian base:query file="tasks" view="Kanban"
obsidian base:query path="folder/tasks.base" format=csv
obsidian base:views file="tasks"
obsidian base:create file="tasks" title="Buy milk"
```

Formats: `json` (default), `csv`, `tsv`, `md`, `paths`

---

## History

File Recovery plugin (distinct from Sync history).

```bash
obsidian history:list
obsidian history path="folder/note.md"
obsidian history:read path="folder/note.md"
obsidian history:read path="folder/note.md" version=3
obsidian history:restore path="folder/note.md" version=3
obsidian history:open path="folder/note.md"
```

---

## Workspace & Tabs

```bash
obsidian workspace
obsidian tabs
obsidian tab:open file="folder/note.md"
obsidian tab:open view="graph"
```

---

## Diff

```bash
obsidian diff path="folder/note.md"
obsidian diff path="folder/note.md" from=1 to=2
obsidian diff path="folder/note.md" filter=local|sync
```

---

## Developer

```bash
obsidian dev:screenshot path="folder/screenshot.png"   # vault-relative path only
obsidian eval code="app.vault.getFiles().length"
obsidian dev:debug on|off
obsidian dev:console limit=20
obsidian dev:errors
obsidian dev:dom selector=".view-content"
obsidian dev:dom selector=".view-content" all|text|total
obsidian dev:dom selector=".view-content" attr=class
obsidian dev:css selector=".view-content"
obsidian dev:css selector=".view-content" prop=color
obsidian devtools
obsidian dev:mobile on|off
```

Multiline eval — write to temp file:
```bash
cat > /tmp/obs.js << 'JS'
var files = app.vault.getMarkdownFiles();
files.length;
JS
obsidian eval code="$(cat /tmp/obs.js)"
```

---

## Vault & System

```bash
obsidian vault
obsidian vaults
obsidian version
obsidian outline path="note.md"
obsidian wordcount path="note.md"
obsidian recents
obsidian reload
obsidian restart
```

---

## Output Formats

| Format | Use |
|---|---|
| `text` | default, pipe-friendly |
| `json` | jq, agents |
| `csv` | spreadsheet |
| `tsv` | cut/awk |
| `yaml` | config |
| `md` | markdown table |
| `paths` | batch ops |
| `tree` | visual hierarchy |

---

## Headless Linux

```bash
Xvfb :5 -screen 0 1920x1080x24 &
DISPLAY=:5 obsidian &
DISPLAY=:5 obsidian daily:read 2>/dev/null
```

Systemd: set `PrivateTmp=false`. Use `.deb` package, not snap.
