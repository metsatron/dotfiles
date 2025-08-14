#!/bin/bash
input="$1"
base="${input%.*}"
pandoc -f markdown "$input" -t org --wrap=none -o "$base.org"
