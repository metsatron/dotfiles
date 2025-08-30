#!/bin/bash
input="$1"
base="${input%.*}"
output="${base}.md"

# 1. Pandoc conversion
pandoc -f html -t gfm --wrap=none -o "$output" "$input"

# 2. Fix .html links to .md
sed -i 's/\.html/.md/g' "$output"

# 3. Optionally strip any leftover raw HTML tags (be careful!)
sed -i '/^</d' "$output"
