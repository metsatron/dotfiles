#!/bin/zsh
# ~/.zshenv -- sourced for ALL zsh invocations (login, interactive, scripts, SSH)
# Keep minimal. Only PATH-critical entries belong here.

# Core PATH entries
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/local/sbin:$PATH"

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
      [ -d "$GUIX_PROFILE/lib/locale" ] && export GUIX_LOCPATH="$GUIX_PROFILE/lib/locale"
      ;;
  esac
fi

# HelmCortex FORGE bin (auryn, pipelines, sapphire-server)
if [ -d "$HOME/HelmCortex/FORGE/bin" ]; then
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

claude_native_dir=

for claude_base in \
  "$HOME/.config/Claude/claude-code" \
  "$HOME/.config/Claude/claude-code-vm"
do
  [ -d "$claude_base" ] || continue
  claude_native_dir="$(command ls -1d "$claude_base"/* 2>/dev/null | sort -V | tail -n 1)"
  if [ -n "$claude_native_dir" ] && [ -x "$claude_native_dir/claude" ]; then
    export PATH="$claude_native_dir:$PATH"
    break
  fi
done

if [ -z "$claude_native_dir" ] && [ -d "$HOME/.antigravity/extensions" ]; then
  claude_native_dir="$(command ls -1d "$HOME"/.antigravity/extensions/anthropic.claude-code-*/resources/native-binary 2>/dev/null | sort -V | tail -n 1)"
  if [ -n "$claude_native_dir" ] && [ -x "$claude_native_dir/claude" ]; then
    export PATH="$claude_native_dir:$PATH"
  fi
fi

unset claude_base claude_native_dir

# Stop Guix libs leaking into host binaries
unset LD_LIBRARY_PATH 2>/dev/null
