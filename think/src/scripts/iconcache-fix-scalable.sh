#!/usr/bin/env bash
set -euo pipefail
theme="${1:?Usage: fix-scalable.sh THEME_DIR}"
moved=0
while IFS= read -r -d '' f; do
  dir="$(dirname "$f")"                  # e.g. apps/scalable
  base="$(basename "$f")"                # e.g. totem.png
  tgt="${dir%/scalable}/48"              # e.g. apps/48
  mkdir -p "$theme/$tgt"
  echo "mv -- $theme/$f $theme/$tgt/$base"
  mv -- "$theme/$f" "$theme/$tgt/$base"
  : $((moved+=1))
done < <(find "$theme" -type d -name scalable -print0 \
        | xargs -0 -I{} find "{}" -type f ! -iname '*.svg' -print0)
echo "Moved $moved file(s) out of scalable dirs."
