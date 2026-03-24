#!/usr/bin/env bash
# Session wiring for Guix profiles

# [[file:../../guix.org::*Session wiring for Guix profiles][Session wiring for Guix profiles:1]]
# Sourced by Xsession under /bin/sh; never enable nounset here.
GUIX_PROFILE="$HOME/.guix-extra-profiles/core/core"
export GUIX_PROFILE
if [ -r "$GUIX_PROFILE/etc/profile" ]; then
  . "$GUIX_PROFILE/etc/profile"
fi
# Session wiring for Guix profiles:1 ends here
