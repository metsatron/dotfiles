#!/bin/bash
# Root. Requires gateway+webui STOPPED. Renames the pre-upgrade trees back. With --restore-state also restores the phase-B state snapshot.
set -euo pipefail; . "$(dirname "$0")/lib.sh"; svc_stopped
for p in "$HH/hermes-agent.pre-upgrade" "$WS/hermes-webui.pre-upgrade"; do [ -d "$p" ] || die "missing $p"; done
TS=$(date +%Y%m%d-%H%M%S)
mv "$HH/hermes-agent" "$HH/hermes-agent.failed-$TS"; mv "$HH/hermes-agent.pre-upgrade" "$HH/hermes-agent"
mv "$WS/hermes-webui" "$WS/hermes-webui.failed-$TS"; mv "$WS/hermes-webui.pre-upgrade" "$WS/hermes-webui"
# Launcher and OpenRC scripts back to their pre-upgrade form (saved by backup-phaseA.sh).
A=$BK/20261106-phaseA
[ -f "$A/hermes-wrapper.orig" ] && install -m 0755 -o "$OWNER" -g "$OWNER" "$A/hermes-wrapper.orig" "$LB/hermes"
for s in hermes-gateway hermes-webui; do [ -f "$A/$s" ] && install -m 0755 "$A/$s" "$INITD/$s"; done
if [ "${1:-}" = "--restore-state" ]; then
  ( cd "$BK/20261106-phaseB" && sha256sum -c SHA256SUMS >/dev/null ) || die "phase B checksum"
  tar --zstd --numeric-owner --xattrs --acls -xpf "$BK/20261106-phaseB/hermes-home.tar.zst" -C "$(dirname "$HH")"
  echo STATE-RESTORED
fi
echo ROLLED-BACK-OK
