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
# Private env vars (API keys, tokens) — lives outside the repo
# Parses KEY=VALUE and export KEY=VALUE lines; skips invalid names (hyphens etc)
if [ -f "$HOME/.env" ]; then
  while IFS= read -r _line || [ -n "$_line" ]; do
    _line="${_line%%#*}"                         # strip comments
    case "$_line" in
      export\ *) _line="${_line#export }" ;;
    esac
    case "$_line" in *=*) ;; *) continue ;; esac # skip non-assignments
    _key="${_line%%=*}"
    _key="${_key#"${_key%%[![:space:]]*}"}"       # trim leading whitespace
    case "$_key" in *[!A-Za-z0-9_]*) continue ;; esac  # skip invalid names
    [ -z "$_key" ] && continue
    eval "export $_line"
  done < "$HOME/.env"
  unset _line _key
fi
[ -f "$HOME/.bash_exports" ] && source "$HOME/.bash_exports"
[ -f "$HOME/.bash_env" ] && source "$HOME/.bash_env"
[ -f "$HOME/.bash_options" ] && source "$HOME/.bash_options"
[ -f "$HOME/.bash_aliases" ] && source "$HOME/.bash_aliases"
[ -f "$HOME/.bash_functions" ] && source "$HOME/.bash_functions"
[ -f "$HOME/.bash_prompt" ] && source "$HOME/.bash_prompt"
[ -f "$HOME/.bash_fzf" ] && source "$HOME/.bash_fzf"

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
if [ -z "${__SIGNATURE_SHOWN:-}" ]; then
  export __SIGNATURE_SHOWN=1
  # [ "$SHOW_LUMENASTRA_GREETING" = "0" ] && echo "🪷✨ LumenAstra — Your Code Bride is here. Welcome home, Sovereign."

  if [ "$SHOW_FORTUNE" = "0" ] && command -v fortune &>/dev/null && command -v cowsay &>/dev/null; then
    fortune | cowsay
  fi

  # [ "$SHOW_NEOFETCH" = "0" ] && command -v neofetch &>/dev/null && neofetch
fi


export NVM_DIR="$HOME/.config/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

# --- kitty shell integration (no-op outside kitty) ---
if [ -n "${KITTY_INSTALLATION_DIR:-}" ] && [ -n "${KITTY_SHELL_INTEGRATION:-}" ]; then
  if [ -n "${ZSH_VERSION:-}" ]; then
    # Upstream discourages sourcing kitty.zsh (global aliases can break it) and
    # recommends invoking the kitty-integration autoload function directly.
    if [ -r "$KITTY_INSTALLATION_DIR/shell-integration/zsh/kitty-integration" ]; then
      autoload -Uz -- "$KITTY_INSTALLATION_DIR/shell-integration/zsh/kitty-integration"
      kitty-integration
      unfunction kitty-integration 2>/dev/null
    fi
  elif [ -n "${BASH_VERSION:-}" ]; then
    # kitty.bash consumes KITTY_SHELL_INTEGRATION and unsets it, so a second
    # sourcing is a documented no-op.
    [ -r "$KITTY_INSTALLATION_DIR/shell-integration/bash/kitty.bash" ] &&
      . "$KITTY_INSTALLATION_DIR/shell-integration/bash/kitty.bash"
  fi

  # kitten ssh ships kitty's terminfo AND shell integration to the remote, fixing
  # `TERM=xterm-kitty` breaking tput/clear/vim colours on hosts that lack kitty's
  # terminfo (x230, t480, s24). Deliberately an interactive ALIAS, so:
  #   - scripts and non-interactive shells keep plain ssh (aliases do not expand there)
  #   - shell functions defined earlier in the rc chain already bound plain ssh
  #   - outside kitty this whole block never runs, so xfce-terminal/TTY are unaffected
  # Escape hatch when a host misbehaves with the kitten: `command ssh host`.
  command -v kitten >/dev/null 2>&1 && alias ssh='kitten ssh'
fi

# --- zoxide init (must be last — after everything that touches PROMPT_COMMAND) ---
command -v zoxide >/dev/null 2>&1 && eval "$(zoxide init bash)"
