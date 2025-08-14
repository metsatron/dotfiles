#!/bin/bash
input="$1"
base="${input%.*}"
pandoc -f odt "$input" -t gfm --wrap=none \
  | sed '/^<!-- -->$/d' \
  | sed 's/\*\+$//' \
  | sed '/^$/N;/^\n$/D' \
  > "$base.md"
