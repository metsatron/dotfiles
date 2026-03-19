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
if [ -r "$HOME/.guix-extra-profiles/core/core/etc/profile" ] && [ -z "${__GUIX_CORE_PROFILE_SOURCED+x}" ]; then
  export __GUIX_CORE_PROFILE_SOURCED=1
  export GUIX_PROFILE="$HOME/.guix-extra-profiles/core/core"
  . "$GUIX_PROFILE/etc/profile"
  [ -d "$GUIX_PROFILE/lib/locale" ] && export GUIX_LOCPATH="$GUIX_PROFILE/lib/locale"
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

# Stop Guix libs leaking into host binaries
unset LD_LIBRARY_PATH 2>/dev/null
