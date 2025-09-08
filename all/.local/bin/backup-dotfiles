#!/usr/bin/env bash
set -euo pipefail

DOT="$HOME/.dotfiles"
BACKUP_ROOT="/backup/backup-dotfiles"
DATE="$(date +%Y%m%d-%H%M%S)"
DEST="$BACKUP_ROOT/dotfiles.$DATE"

# Check if .dotfiles exists
if [ ! -d "$DOT" ]; then
  echo "ERROR: $DOT not found."
  exit 1
fi

# Ensure backup root exists
mkdir -p "$BACKUP_ROOT"

# Rsync copy with archive, hardlinks, and progress
rsync -aHAX --info=progress2 --delete "$DOT/" "$DEST/"

echo "Backup complete: $DEST"
