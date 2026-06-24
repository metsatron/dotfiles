#!/usr/bin/env sh
# Start the registrar inside the real X session so exported menus and the
# panel plugin meet on the same session bus.
#
# IMPORTANT: this runs at Xsession step 40 (xsessionrc), before D-Bus is
# created at step 75 (dbus-launch). Without a live session bus the registrar
# cannot connect and silently exits. The boot autostart (appmenu-boot.desktop)
# handles the common case; this snippet is a belt-and-suspenders fallback for
# display managers that start D-Bus before running Xsession (e.g. systemd/GDM).
[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ] || return 0

registrar_has_owner() {
  command -v gdbus >/dev/null 2>&1 || return 1
  gdbus call --session \
    --dest org.freedesktop.DBus \
    --object-path /org/freedesktop/DBus \
    --method org.freedesktop.DBus.NameHasOwner \
    com.canonical.AppMenu.Registrar 2>/dev/null | grep -q '(true,'
}

APPMENU_REGISTRAR=
if ! registrar_has_owner; then
  pkill -x appmenu-registr >/dev/null 2>&1 || true
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
