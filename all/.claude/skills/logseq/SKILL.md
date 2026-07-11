---
name: logseq
description: Interact with Logseq DB via native logseq CLI (auto-installed at ~/.local/bin/logseq) or HTTP API (port 12315). CLI requires Logseq GUI running. Use for querying pages, blocks, tasks, tags; running queries; appending content.
---

# Logseq DB

Use this skill when interacting with Logseq's knowledge base: querying pages, blocks, tasks,
tags, or properties; running Datascript queries; or navigating to specific pages.

## Native CLI (Primary)

Logseq auto-installs a `logseq` CLI launcher at `~/.local/bin/logseq` each time the GUI starts.
The launcher uses `ELECTRON_RUN_AS_NODE=1` against the active AppImage mount — it connects to
the running db-worker-node (port 38339) and does not open a display.

**Prerequisite:** Logseq GUI must be running (it starts the db-worker-node and updates the launcher).

```bash
logseq --help                                  # top-level commands and global flags
logseq <command> --help                        # command-specific options
logseq example                                 # runnable examples (source of truth)
logseq example <command>                       # examples for a specific command
```

Key global flags: `--graph GRAPH_NAME`, `--output json|edn|human`, `--root-dir PATH`

Command groups:
- Inspect/edit: `list node|page|tag|property|task|asset`
- Write: `upsert block|page|tag|property|task`
- Delete: `remove block|page|tag|property`
- Query: `query`, `query list`, `show`, `search block|page|property|tag`
- Graph lifecycle: `graph list|create|switch|remove|validate|info|export|import|backup|sync`
- Server: `server list|start|stop|restart|cleanup`
- Auth: `login|logout`

**Always use `logseq <cmd> --help` for live options and `logseq example <cmd>` for examples.**

```bash
logseq list page --graph LOGS --output json    # list all pages in LOGS graph
logseq show --graph LOGS --id 12345            # show a block or page by db/id
logseq search page --graph LOGS "keyword"      # search pages
logseq upsert block --graph LOGS --target-page "Journal" --content "new note"
logseq upsert task --graph LOGS --target-page "Tasks" --content "do something" --status todo
```

## HTTP API (Alternative)

Requires enabling in Logseq Settings -> Features -> HTTP APIs server.
Token stored at `~/.logseq/api-token`.

```bash
logseq-api check                                          # verify API at port 12315
logseq-api logseq.Editor.getAllPages                      # list all pages
logseq-api logseq.Editor.getPageBlocksTree '["Page"]'    # blocks on a page
logseq-api logseq.Editor.appendBlockInPage '["Page", "content"]'
logseq-api logseq.search '["query"]'
```

## Navigation (logseq:// URL Scheme)

```bash
xdg-open "logseq://graph/GRAPH_NAME/page/PAGE_NAME"
ls ~/logseq/graphs/    # available graph names
```

## State Discovery

```bash
ls ~/logseq/graphs/              # graph names (directories)
cat ~/logseq/server-list         # PID PORT of running db-worker-node
logseq server list               # server status via CLI
```

## SQLite Fallback (Offline / Read-Only)

```bash
GRAPH=LOGS
cp "$HOME/logseq/graphs/$GRAPH/db.sqlite" /tmp/logseq-snap.sqlite
sqlite3 /tmp/logseq-snap.sqlite "SELECT content FROM kvs LIMIT 5;"
```

Content is Transit+JSON encoded DataScript — use text matching for simple reads only.
