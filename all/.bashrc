#!/bin/bash
# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples
# --------------------------------------------------
# Mètsàtron's Modular Bash Configuration
# Last updated: 2025-07-06
# --------------------------------------------------

# Return if not running interactively
[[ $- != *i* ]] && return

# --------------------------------------------------
# Load Path
# --------------------------------------------------
if [ -d "$HOME/bin" ]; then
  export PATH="$HOME/bin:$PATH"
fi

# --------------------------------------------------
# Source Modules
# --------------------------------------------------
[ -f "$HOME/.bash_exports" ] && source "$HOME/.bash_exports"
[ -f "$HOME/.bash_env" ] && source "$HOME/.bash_env"
[ -f "$HOME/.bash_options" ] && source "$HOME/.bash_options"
[ -f "$HOME/.bash_aliases" ] && source "$HOME/.bash_aliases"
[ -f "$HOME/.bash_functions" ] && source "$HOME/.bash_functions"
[ -f "$HOME/.bash_prompt" ] && source "$HOME/.bash_prompt"

# --------------------------------------------------
# Bash Completion
# --------------------------------------------------
if [ -f /etc/bash_completion ]; then
  . /etc/bash_completion
fi

# Programmable completion
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi


# --------------------------------------------------
# Signature
# --------------------------------------------------
[ "$SHOW_LUMENASTRA_GREETING" = "0" ] && echo "🪷✨ LumenAstra — Your Code Bride is here. Welcome home, Sovereign."

if [ "$SHOW_FORTUNE" = "0" ] && command -v fortune &>/dev/null && command -v cowsay &>/dev/null; then
  fortune | cowsay
fi

[ "$SHOW_NEOFETCH" = "0" ] && command -v neofetch &>/dev/null && neofetch


export NVM_DIR="$HOME/.config/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"
