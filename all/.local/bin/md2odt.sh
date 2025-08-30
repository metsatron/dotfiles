#!/bin/bash
input="$1"
base="${input%.*}"
pandoc -t odt "$input" -o "$base.odt"
