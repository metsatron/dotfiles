#!/usr/bin/env sh
# Start the registrar inside the real X session so exported menus and the
# panel plugin meet on the same session bus.
registrar_reachable() {
  command -v gdbus >/dev/null 2>&1 || return 1
  gdbus call --session \
    --dest com.canonical.AppMenu.Registrar \
    --object-path /com/canonical/AppMenu/Registrar \
    --method org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1
}

APPMENU_REGISTRAR=
if ! registrar_reachable; then
  pkill -x appmenu-registrar >/dev/null 2>&1 || true

  if command -v appmenu-registrar >/dev/null 2>&1; then
    APPMENU_REGISTRAR="$(command -v appmenu-registrar)"
  elif [ -x /usr/libexec/vala-panel/appmenu-registrar ]; then
    APPMENU_REGISTRAR=/usr/libexec/vala-panel/appmenu-registrar
  fi

  if [ -n "${APPMENU_REGISTRAR}" ]; then
    # Keep the registrar alive after the helper shell exits.
    nohup "$APPMENU_REGISTRAR" -r >/dev/null 2>&1 &
  fi
fi

unset APPMENU_REGISTRAR
