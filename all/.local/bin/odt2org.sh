#!/bin/bash
input="$1"
base="${input%.*}"
pandoc -f odt "$input" -t org --wrap=none -o "$base.org"
