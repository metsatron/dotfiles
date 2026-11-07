#!/usr/bin/env bash
# Locked ingest body for the Aura recall-ingest hook. Re-export sessions from
# state.db (canonical exporter) then add-only index into Odysseus (add_document
# skips already-stored chunks by content-hash, so only new chunks embed). Only
# touches aura_conversations + Obsidian Vault — never the Secret Vault.
LOG=/home/gille/.hermes/logs/aura_recall_ingest.log
{
  echo "[$(date '+%F %T')] recall-ingest start (pid $$)"
  python3 /opt/odysseus/data/_export_aura_conversations.py 2>&1 | tail -1
  docker exec -i odysseus-odysseus-1 python - <<'PY' 2>&1 | tail -1
import sys; sys.path.insert(0, "/app")
from src.rag_singleton import get_rag_manager
m = get_rag_manager()
r = m.index_personal_documents("/app/data/aura_conversations")
print("indexed=%s failed=%s" % (r.get("indexed_count"), r.get("failed_count")))
PY
  echo "[$(date '+%F %T')] recall-ingest done"
} >> "$LOG" 2>&1
