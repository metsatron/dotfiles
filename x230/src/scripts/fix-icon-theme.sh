#!/usr/bin/env bash
set -euo pipefail
THEME="${1:-$HOME/.local/share/icons/BeOS-r5-Icons}"
cd "$THEME"

# 0) backup (if present)
cp -a index.theme index.theme.bak.$(date +%s) 2>/dev/null || true

# 1) collect ONLY real size/context dirs at depth 2 (apps/48, status/scalable, etc.)
DIRS=$(find . -mindepth 2 -maxdepth 2 -type d \
  -regextype posix-extended \
  -regex './(actions|animations|apps|categories|devices|emblems|emotes|mimes|notifications|panel|places|status|stock)/(scalable|symbolic|[0-9]+)' \
  -printf '%P\n' | LC_ALL=C sort -u)

# 2) write a minimal, spec-correct index.theme that matches the tree
{
  echo '[Icon Theme]'
  echo 'Name=BeOS-r5-Icons'
  echo 'Comment=Classic icons'
  printf 'Directories='; echo "$DIRS" | paste -sd, -
  echo
  while read -r d; do
    [ -n "$d" ] || continue
    size="${d##*/}"
    echo "[$d]"
    if [[ "$size" =~ ^[0-9]+$ ]]; then
      echo "Size=$size"
      echo "Type=Fixed"      # PNG sizes
    else
      echo "Size=48"
      echo "Type=Scalable"   # for scalable/symbolic dirs (SVG)
      echo "MinSize=1"
      echo "MaxSize=512"
    fi
    echo
  done <<< "$DIRS"
} > index.theme

# 3) rebuild cache (index-only first, then full)
gtk-update-icon-cache -f -i "$THEME"
gtk-update-icon-cache -f "$THEME"
