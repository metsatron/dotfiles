#!/bin/zsh
# Metsatron's .zshrc

# Modular includes (interactive only) — your wildcard loader
if [[ $- == *i* ]]; then
  for file in $HOME/DotCortex/all/.zsh_*; do
    [ -f "$file" ] && source "$file"
  done
fi
