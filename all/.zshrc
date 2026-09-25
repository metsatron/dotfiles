#!/bin/zsh
# Metsatron's .zshrc

# Private keys (~/.env) are NOT exported into the shell (2026-09-25): every
# agent launched from a terminal inherited them, and one `env` in its tool
# calls would ship them to its model provider. Tools load their own keys at
# runtime. For one command: `withkeys NAME... -- cmd`. Into this shell, on
# purpose: `loadkeys NAME...`. List names: `withkeys --list`.
loadkeys() { eval "$(withkeys --emit "$@")"; }

# Modular includes (interactive only) — your wildcard loader
if [[ $- == *i* ]]; then
  for file in $HOME/DotCortex/all/.zsh_*; do
    [ -f "$file" ] && source "$file"
  done
fi

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
