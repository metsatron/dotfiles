#!/usr/bin/env sh
command -v gsettings >/dev/null 2>&1 || return 0

THEME_NAME=""
if command -v xfconf-query >/dev/null 2>&1; then
  THEME_NAME="$(xfconf-query -c xsettings -p /Net/ThemeName 2>/dev/null)"
fi

case "${THEME_NAME}" in
  *[Dd]ark*) SCHEME=prefer-dark ;;
  *)         SCHEME=default ;;
esac

gsettings set org.gnome.desktop.interface color-scheme "${SCHEME}" 2>/dev/null || true
