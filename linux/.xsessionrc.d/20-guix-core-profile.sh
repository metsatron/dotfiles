#!/usr/bin/env bash
# Session wiring for Guix profiles

# [[file:../../package-guix.org::*Session wiring for Guix profiles][Session wiring for Guix profiles:1]]
# Sourced by Xsession under /bin/sh; never enable nounset here.
GUIX_PROFILE="$HOME/.guix-extra-profiles/core/core"
export GUIX_PROFILE
if [ -r "$GUIX_PROFILE/etc/profile" ]; then
  . "$GUIX_PROFILE/etc/profile"
fi

# Guix's glibc finds locale data only via GUIX_LOCPATH. The profile's own
# etc/profile does NOT export it, and the X session never sets it, so a
# Guix binary launched from a keyboard shortcut or autostart entry sees
# LANG=en_US.UTF-8 with no locale data behind it. Two failure modes follow,
# and both were observed: rofi calls setlocale(), fails, and exits 1 (every
# rofi shortcut silently dead); or, with LANG also unset, it starts in the C
# locale, where fontconfig scores Noto Color Emoji below Symbola and colour
# emoji degrade into outline glyphs and tofu. An interactive zsh escapes both
# because .zshenv sets GUIX_LOCPATH -- which is why `rofi -dmenu` from a
# terminal always worked while the identical shortcut did not.
if [ -d "$GUIX_PROFILE/lib/locale" ]; then
  GUIX_LOCPATH="$GUIX_PROFILE/lib/locale"
  export GUIX_LOCPATH
fi

add_xdg_data_dir() {
  dir="$1"
  [ -d "$dir" ] || return 0
  case ":${XDG_DATA_DIRS:-}:" in
    *":$dir:"*) ;;
    *) XDG_DATA_DIRS="${XDG_DATA_DIRS:+$XDG_DATA_DIRS:}$dir" ;;
  esac
}

old_xdg_data_dirs="${XDG_DATA_DIRS:-}"
XDG_DATA_DIRS=""
old_ifs="$IFS"
IFS=:
for dir in $old_xdg_data_dirs; do
  add_xdg_data_dir "$dir"
done
IFS="$old_ifs"

# Guix profile activation can leave XDG_DATA_DIRS containing only the profile
# currently sourced. Desktop menus need every active Guix profile plus the
# system application directories.
for profile in "$HOME/.guix-profile" "$HOME"/.guix-extra-profiles/*/*; do
  [ -d "$profile" ] || continue
  case "$profile" in
    *-link) continue ;;
    # Room and sanctuary profiles belong to their own rooms/containers, which
    # source them explicitly. Adding their share/ to the HOST session's
    # XDG_DATA_DIRS ranks their .desktop files ABOVE /usr/share, so a Guix build
    # silently shadows the Debian app -- its Exec= is an absolute /gnu/store path,
    # so PATH never even comes into it. A Guix GTK app resolves modules and themes
    # from the Guix store, so it cannot load Debian's appmenu-gtk-module and loses
    # the global menu, and falls back to Adwaita/CSD instead of the host GTK theme.
    # This is exactly what broke pluma's global menu (room-gaming ships pluma).
    # Rooms stay out of the host session.
    "$HOME"/.guix-extra-profiles/room-*|"$HOME"/.guix-extra-profiles/sanctuary-*) continue ;;
  esac
  add_xdg_data_dir "$profile/share"
done
add_xdg_data_dir "$HOME/.local/share/flatpak/exports/share"
add_xdg_data_dir /var/lib/flatpak/exports/share
add_xdg_data_dir /usr/local/share
add_xdg_data_dir /usr/share
export XDG_DATA_DIRS

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

# The Guix profile sets GST_PLUGIN_SYSTEM_PATH to ONLY its own plugin dir. That
# var REPLACES (does not append to) GStreamer's compiled-in OS default, so every
# system app in this session (e.g. Debian Quod Libet, GStreamer 1.26) stops
# scanning /usr/lib/.../gstreamer-1.0 and loses pulsesink -> playback dies with
# "No GStreamer audio sink found". This runs once for the whole session, so it
# fixes every GUI app regardless of which shell launches it. Append the OS
# plugin dirs back: each GStreamer core silently skips version-mismatched
# plugins, so Guix (1.28) and system (1.26) apps each keep their own set.
if [ -n "${GST_PLUGIN_SYSTEM_PATH:-}" ]; then
  for __gst in "/usr/lib/$(uname -m)-linux-gnu/gstreamer-1.0" /usr/lib/gstreamer-1.0 /usr/lib64/gstreamer-1.0; do
    [ -d "$__gst" ] || continue
    case ":$GST_PLUGIN_SYSTEM_PATH:" in
      *":$__gst:"*) ;;
      *) GST_PLUGIN_SYSTEM_PATH="$GST_PLUGIN_SYSTEM_PATH:$__gst" ;;
    esac
  done
  export GST_PLUGIN_SYSTEM_PATH
  unset __gst
fi
# Session wiring for Guix profiles:1 ends here
