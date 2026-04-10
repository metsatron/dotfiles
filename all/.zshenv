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

# ~/.local/bin/claude is canonical. If it is absent, fall back to the newest
# native Claude binary under ~/.config/Claude or Antigravity.
if ! command -v claude >/dev/null 2>&1; then
  claude_native_dir=

  for claude_base in \
    "$HOME/.config/Claude/claude-code" \
    "$HOME/.config/Claude/claude-code-vm"
  do
    [ -d "$claude_base" ] || continue
    claude_native_dir="$(find "$claude_base" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort -V | tail -n 1)"
    if [ -n "$claude_native_dir" ] && [ -x "$claude_native_dir/claude" ]; then
      export PATH="$claude_native_dir:$PATH"
      break
    fi
  done

  if [ -z "$claude_native_dir" ] && [ -d "$HOME/.antigravity/extensions" ]; then
    _claude_dir="$(find "$HOME/.antigravity/extensions" -path '*/resources/native-binary' -type d 2>/dev/null | sort -V | tail -n 1)"
    if [ -n "${_claude_dir:-}" ] && [ -x "$_claude_dir/claude" ]; then
      export PATH="$_claude_dir:$PATH"
    fi
    unset _claude_dir
  fi

  unset claude_base claude_native_dir
fi

# Stop Guix libs leaking into host binaries
unset LD_LIBRARY_PATH 2>/dev/null
