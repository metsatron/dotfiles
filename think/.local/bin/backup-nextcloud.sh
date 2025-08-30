#!/usr/bin/env bash

# === CONFIGURATION ===
SOURCE="$HOME/Nextcloud"
DEST_1="/usr/share/pool/Nextcloud"
DEST_2="/backup/Nextcloud"

# Optional: Change log file locations if needed
LOG_DIR="/tmp"
LOG_1="$LOG_DIR/rsync_nextcloud_pool.log"
LOG_2="$LOG_DIR/rsync_nextcloud_backup.log"

# === FUNCTIONS ===
sync_folder() {
  local source="$1"
  local dest="$2"
  local log="$3"

  echo "[*] Syncing $source → $dest"
  rsync -avh --delete --checksum --progress "$source/" "$dest/" | tee "$log"
  echo "[✓] Finished syncing to $dest"
}

# === EXECUTION ===
echo "🌕 Starting Nextcloud dual sync: $(date)"
sync_folder "$SOURCE" "$DEST_1" "$LOG_1"
sync_folder "$SOURCE" "$DEST_2" "$LOG_2"
echo "🌕 Dual sync complete: $(date)"

