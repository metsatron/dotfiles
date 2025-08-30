#!/bin/bash
input="$1"
base="${input%.*}"
pandoc -f org "$input" -t gfm --wrap=none -o "$base.md"
