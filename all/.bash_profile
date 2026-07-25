#!/bin/bash
# ~/.bash_profile

# PATH first, and independently of .bashrc. .bashrc returns immediately for a
# non-interactive shell ([[ $- != *i* ]] && return), so a login-but-not-
# interactive bash -- scripts, cron, ssh commands, .desktop launchers -- never
# reached .bash_exports and came up with neither ~/.local/bin nor the HelmCortex
# shims on PATH. Sourcing it here fixes that; the dedupe inside shared-exports-min
# makes the second pass via .bashrc harmless.
if [ -f "$HOME/.bash_exports" ]; then
    . "$HOME/.bash_exports"
fi

# Source .bashrc if it exists
if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi

# Add any login-specific commands here

[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"
