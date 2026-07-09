#!/bin/sh
case "$1" in
  dark)  SCHEME=prefer-dark ;;
  light) SCHEME=default ;;
esac
gsettings set org.gnome.desktop.interface color-scheme "${SCHEME}" 2>/dev/null || true
