# Shared by the deploy scripts. Paths are overridable ONLY for the /tmp rehearsal.
: "${HH:=/home/gille/.hermes}"            # hermes home
: "${WS:=/home/gille/src}"                # webui parent
: "${BK:=/var/lib/hermes-upgrade/backups}"
: "${LB:=/home/gille/.local/bin}"         # launcher directory
: "${INITD:=/etc/init.d}"
: "${OWNER:=gille}"
: "${RC:=rc-service}"
: "${SKIP_PROC_CHECK:=0}"
die(){ echo "ABORT: $*" >&2; exit 1; }
svc_stopped(){ for s in hermes-gateway hermes-webui; do out=$($RC $s status 2>&1 || true); echo "$out" | grep -q "stopped" || die "$s not stopped: $out"; done
  if [ "$SKIP_PROC_CHECK" != 1 ]; then ps -eo cmd | grep -E "hermes gateway run|hermes-webui/server.py" | grep -v grep && die "hermes process still alive" || true; fi; }
