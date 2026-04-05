#!/usr/bin/env bash
# Session wiring for Guix profiles

# [[file:../../guix.org::*Session wiring for Guix profiles][Session wiring for Guix profiles:1]]
# Sourced by Xsession under /bin/sh; never enable nounset here.
GUIX_PROFILE="$HOME/.guix-extra-profiles/core/core"
export GUIX_PROFILE
if [ -r "$GUIX_PROFILE/etc/profile" ]; then
  . "$GUIX_PROFILE/etc/profile"
fi
# The Guix profile sets GIO_EXTRA_MODULES to its own gio/modules dir, which
# contains GIO modules built against Guix GLib (currently 2.83+). System
# binaries (flatpak-session-helper, xdg-desktop-portal) link against the
# system GLib (2.72 on Ubuntu 22.04) and lack newer symbols like
# g_once_init_enter_pointer — causing them to crash on startup.
#
# /etc/X11/Xsession.d/95dbus_update-activation-env runs after this script and
# calls `dbus-update-activation-environment --systemd --all`, which bakes the
# entire current environment — including GIO_EXTRA_MODULES — into the systemd
# user session. Removing it from the systemd session here, before step 95
# runs, prevents it from ever reaching system service processes.
#
# Guix-built apps find their own GIO modules via their compiled-in rpath
# (/gnu/store/.../lib/gio/modules), so this does not break Guix apps.
if systemctl --user is-active --quiet default.target 2>/dev/null; then
  systemctl --user unset-environment GIO_EXTRA_MODULES 2>/dev/null || true
fi
unset GIO_EXTRA_MODULES
# Session wiring for Guix profiles:1 ends here
