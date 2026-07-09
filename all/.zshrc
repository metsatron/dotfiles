#!/bin/zsh
# Metsatron's .zshrc

# Private env vars (API keys, tokens) — lives outside the repo
# Parses KEY=VALUE and export KEY=VALUE lines; skips invalid names (hyphens etc)
if [[ -f "$HOME/.env" ]]; then
  while IFS= read -r _line || [[ -n "$_line" ]]; do
    _line="${_line%%#*}"
    case "$_line" in
      export\ *) _line="${_line#export }" ;;
    esac
    case "$_line" in *=*) ;; *) continue ;; esac
    _key="${_line%%=*}"
    _key="${_key#"${_key%%[![:space:]]*}"}"
    case "$_key" in *[!A-Za-z0-9_]*) continue ;; esac
    [[ -z "$_key" ]] && continue
    eval "export $_line"
  done < "$HOME/.env"
  unset _line _key
fi

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
