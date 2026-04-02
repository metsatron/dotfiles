#!/usr/bin/env sh
# Start the registrar inside the real X session so exported menus and the
# panel plugin meet on the same session bus.
APPMENU_REGISTRAR=
if command -v appmenu-registrar >/dev/null 2>&1; then
  APPMENU_REGISTRAR="$(command -v appmenu-registrar)"
elif [ -x /usr/libexec/vala-panel/appmenu-registrar ]; then
  APPMENU_REGISTRAR=/usr/libexec/vala-panel/appmenu-registrar
fi

if [ -n "${APPMENU_REGISTRAR}" ]; then
  if ! pgrep -af '[a]ppmenu-registrar' >/dev/null 2>&1; then
    "$APPMENU_REGISTRAR" -r >/dev/null 2>&1 &
  fi
fi

unset APPMENU_REGISTRAR
