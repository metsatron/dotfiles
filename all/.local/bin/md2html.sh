#!/bin/bash
input="$1"
base="${input%.*}"
pandoc -f markdown -t html5 --standalone --css=$HOME/.dotfiles/all/.css/splendor/splendor.css -o "${base}.html" "$input"
