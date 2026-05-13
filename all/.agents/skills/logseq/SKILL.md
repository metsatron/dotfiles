---
name: logseq
description: Interact with Logseq DB via HTTP API (port 12315) and logseq:// URL scheme. Use logseq-api helper to query pages, append blocks, and navigate.
model: claude-haiku-4-5-20251001
---

# Logseq DB

Use this skill when interacting with Logseq's knowledge base: querying pages, appending blocks, or navigating to specific pages.

## HTTP API (Primary)

Logseq DB version exposes the Plugin SDK via HTTP at `http://127.0.0.1:12315/api`.

**Enable once (in Logseq UI):** Settings → Features → HTTP APIs server → Enable → Generate token

**Store the token:**
```bash
mkdir -p ~/.logseq
echo "YOUR_TOKEN" > ~/.logseq/api-token
chmod 600 ~/.logseq/api-token
```

**Helper:** `logseq-api METHOD [ARGS_JSON]` (at `~/.local/bin/logseq-api`)

### Common Methods

```bash
logseq-api check                                                          # verify API is reachable
logseq-api logseq.Editor.getAllPages                                      # list all pages
logseq-api logseq.Editor.getPage '["PageName"]'                          # get a page
logseq-api logseq.Editor.getPageBlocksTree '["PageName"]'                # all blocks on a page
logseq-api logseq.Editor.appendBlockInPage '["PageName", "content"]'    # append a block
logseq-api logseq.Editor.createPage '["NewPage", {}, {"redirect": false}]'
logseq-api logseq.search '["query text"]'
```

All Plugin SDK methods work: `logseq.Editor.*`, `logseq.App.*`, `logseq.DB.*`

## Navigation (logseq:// URL Scheme)

```bash
xdg-open "logseq://graph/GRAPH_NAME/page/PAGE_NAME"
ls ~/logseq/graphs/    # get graph names
```

## State Discovery

```bash
cat ~/logseq/server-list    # PID PORT of running Logseq DB worker
ls ~/logseq/graphs/         # available graph names
logseq-api check            # verify HTTP API is up
```

## SQLite Fallback (Offline / Read-Only)

When Logseq is not running or HTTP API is disabled:

```bash
GRAPH=LOGS
snap="/tmp/logseq-snap.sqlite"
cp "$HOME/logseq/graphs/$GRAPH/db.sqlite" "$snap"
sqlite3 "$snap" "SELECT content FROM kvs LIMIT 5;"
```

The `kvs` table stores Transit+JSON encoded DataScript. Use text matching for simple reads.
