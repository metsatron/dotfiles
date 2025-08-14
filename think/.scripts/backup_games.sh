#!/usr/bin/env bash

# === CONFIGURATION ===
SRC="$HOME/Games"
DEST="/backup/Games"
TRASH_LOG="/tmp/deleted_games_files.log"
FINAL_PURGE_LOG="/tmp/hardlink_purge_games.log"
VOLUME_ROOT="/backup"
DRY_RUN=false  # Set to false to enable actual deletion

# === STEP 1: SYNC & LOG DELETED FILES ===
echo "[*] Running rsync with --delete and logging deletions..."

rsync -a --delete --itemize-changes "$SRC/" "$DEST/" \
  | grep '^*deleting ' \
  | sed 's/^*deleting //' \
  > "$TRASH_LOG"

echo "[*] Deleted files logged in: $TRASH_LOG"

# === STEP 2: DRY RUN HARDLINK PURGE ===
echo "[*] Starting hard link sweep (DRY RUN = $DRY_RUN)..."

> "$FINAL_PURGE_LOG"

while IFS= read -r rel_path; do
  deleted_file="$DEST/$rel_path"
  source_file="$SRC/$rel_path"

  [[ -f "$deleted_file" ]] && continue

  inode=$(stat -c %i "$source_file" 2>/dev/null || true)
  [[ -z "$inode" ]] && continue

  echo "[*] Found inode: $inode for $rel_path" >> "$FINAL_PURGE_LOG"

  if $DRY_RUN; then
    find "$VOLUME_ROOT" -xdev -inum "$inode" -print >> "$FINAL_PURGE_LOG"
  else
    find "$VOLUME_ROOT" -xdev -inum "$inode" -exec rm -v {{}} \; >> "$FINAL_PURGE_LOG"
  fi

done < "$TRASH_LOG"

echo "[*] Sweep complete. See: $FINAL_PURGE_LOG"
