#!/bin/sh
# acpid lid action — DPMS blank/unblank only
# Reads the authoritative lid state from =/proc/acpi/button/lid= rather than
# trusting the acpi event string (its close/open payload format is not
# consistent across kernel versions). Runs as root (acpid's own user), so it
# talks to the real Xorg server via SLiM's own auth cookie rather than any
# per-user =~/.Xauthority= — this keeps it independent of which desktop
# session (host or a nested sanctuary Xephyr/Xnest one) happens to be
# focused.

# [[file:../../../../../services.org::*acpid lid action — DPMS blank/unblank only][acpid lid action — DPMS blank/unblank only:1]]
export DISPLAY=:0
export XAUTHORITY=/var/run/slim.auth

state="$(cat /proc/acpi/button/lid/*/state 2>/dev/null | awk '{print $NF}')"
logger -t dotcortex-lid "invoked, lid state=${state:-unknown}"

case "$state" in
  closed) xset dpms force off; logger -t dotcortex-lid "dpms force off rc=$?" ;;
  open)   xset dpms force on;  logger -t dotcortex-lid "dpms force on rc=$?" ;;
  *)      logger -t dotcortex-lid "unrecognized lid state '$state', no DPMS action taken" ;;
esac
# acpid lid action — DPMS blank/unblank only:1 ends here
