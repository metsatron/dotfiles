#!/bin/zsh
# ~/.zshenv -- sourced for ALL zsh invocations (login, interactive, scripts, SSH)
# Keep minimal. Only PATH-critical entries belong here.

# Core PATH entries
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/local/sbin:$PATH"

# Homebrew / Linuxbrew
if [ -d "/home/linuxbrew/.linuxbrew/bin" ]; then
  export HOMEBREW_PREFIX="${HOMEBREW_PREFIX:-/home/linuxbrew/.linuxbrew}"
  export PATH="$HOMEBREW_PREFIX/bin:$HOMEBREW_PREFIX/sbin:$PATH"
elif [ -d "/opt/homebrew/bin" ]; then
  export HOMEBREW_PREFIX="${HOMEBREW_PREFIX:-/opt/homebrew}"
  export PATH="$HOMEBREW_PREFIX/bin:$HOMEBREW_PREFIX/sbin:$PATH"
fi

# Guix current channel
if [ -d "$HOME/.config/guix/current/bin" ]; then
  export PATH="$HOME/.config/guix/current/bin:$PATH"
fi

# Guix core profile (emacs, nvim, zsh, etc)
# Guard: skip if already sourced AND PATH actually contains the bin dir.
# If the profile sourcing failed silently (e.g. store not ready at boot),
# the guard var may be set but PATH won't have the bin dir — retry in that case.
if [ -r "$HOME/.guix-extra-profiles/core/core/etc/profile" ]; then
  case ":$PATH:" in
    *":$HOME/.guix-extra-profiles/core/core/bin:"*) ;;  # already in PATH, skip
    *)
      export __GUIX_CORE_PROFILE_SOURCED=1
      export GUIX_PROFILE="$HOME/.guix-extra-profiles/core/core"
      . "$GUIX_PROFILE/etc/profile"
      # Guix profile sets EMACSLOADPATH without trailing : so Emacs loses defaults (cl-lib etc)
      [[ -n "${EMACSLOADPATH:-}" && "${EMACSLOADPATH}" != *: ]] && export EMACSLOADPATH="${EMACSLOADPATH}:"
      [ -d "$GUIX_PROFILE/lib/locale" ] && export GUIX_LOCPATH="$GUIX_PROFILE/lib/locale"
      ;;
  esac
fi

# HelmCortex FORGE bin (auryn, pipelines, sapphire-server)
if [ -d "$HOME/HelmCortex/FORGE/bin" ] && ls -d "$HOME/HelmCortex/FORGE/bin" >/dev/null 2>&1; then
  export PATH="$HOME/HelmCortex/FORGE/bin:$PATH"
fi

# fnm (fast node manager)
FNM_PATH="$HOME/.local/share/fnm"
if [ -d "$FNM_PATH" ]; then
  export PATH="$FNM_PATH:$PATH"
fi

# npm global
if [ -d "$HOME/.npm-global/bin" ]; then
  export PATH="$HOME/.npm-global/bin:$PATH"
fi

# Priority: ~/.local/bin/claude (canonical) > ~/.config/Claude native app >
# Antigravity/VSCodium extension > npm global.
# Always prepend the best native binary so it wins over any npm-installed claude.
_claude_found=

# Tier 1: ~/.local/bin/claude (managed symlink / manual install)
if [ -x "$HOME/.local/bin/claude" ]; then
  export PATH="$HOME/.local/bin:$PATH"
  _claude_found=local

# Tier 2: newest versioned dir under Claude app install locations
else
  for _claude_base in \
    "$HOME/.config/Claude/claude-code" \
    "$HOME/.config/Claude/claude-code-vm"
  do
    [ -d "$_claude_base" ] || continue
    _claude_native_dir="$(find "$_claude_base" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort -V | tail -n 1)"
    if [ -n "$_claude_native_dir" ] && [ -x "$_claude_native_dir/claude" ]; then
      export PATH="$_claude_native_dir:$PATH"
      _claude_found=native
      break
    fi
  done

  # Tier 3: Antigravity / VSCodium extension managed binary
  if [ -z "$_claude_found" ] && [ -d "$HOME/.antigravity/extensions" ]; then
    _claude_ext_dir="$(find "$HOME/.antigravity/extensions" -path '*/resources/native-binary' -type d 2>/dev/null | sort -V | tail -n 1)"
    if [ -n "${_claude_ext_dir:-}" ] && [ -x "$_claude_ext_dir/claude" ]; then
      export PATH="$_claude_ext_dir:$PATH"
      _claude_found=antigravity
    fi
    unset _claude_ext_dir
  fi

  unset _claude_base _claude_native_dir
fi

unset _claude_found

# Stop Guix libs leaking into host binaries
unset LD_LIBRARY_PATH 2>/dev/null
