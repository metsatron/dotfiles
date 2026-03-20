#!/bin/zsh
# Metsatron's .zshrc

# Private env vars (API keys, tokens) — lives outside the repo
# Parses KEY=VALUE and export KEY=VALUE lines; skips invalid names (hyphens etc)
if [[ -f "$HOME/.env" ]]; then
  while IFS= read -r _line || [[ -n "$_line" ]]; do
    _line="${_line%%#*}"
    case "$_line" in export\ *) _line="${_line#export }" ;; esac
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

# bun completions
[ -s "/home/metsatron/DotCortex/all/.bun/_bun" ] && source "/home/metsatron/DotCortex/all/.bun/_bun"
