#!/bin/zsh
# Metsatron's .zshrc

# Guard interactive
# if [[ $- == *i* ]]; then
#   neofetch --ascii ~/.local/share/neofetch/CoplandOS.neofetch --ascii_colors 6 4
# fi

# Powerlevel10k Instant Prompt
if [[ $- == *i* ]]; then
  if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
    source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
  fi
fi

# Modular includes (only in interactive)
if [[ $- == *i* ]]; then
  for file in $HOME/.dotfiles/all/.zsh_*; do
    [ -f "$file" ] && source "$file"
  done
fi

# zplug auto-update (optional, may want this even in non-interactive?)
if [[ $- == *i* ]]; then
  zplug check || zplug install
  [[ -z "$(zplug check | grep 'out-of-date')" ]] || zplug update
fi

# Powerlevel10k prompt
if [[ $- == *i* ]]; then
  source ~/.p10k.zsh
fi
