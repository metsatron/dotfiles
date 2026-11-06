#!/bin/bash
# Root. Swap staged trees in by rename. Old trees are KEPT as *.pre-upgrade (rollback = rename back).
set -euo pipefail; . "$(dirname "$0")/lib.sh"; svc_stopped
[ -f "$BK/20261106-phaseA/.done" ] && [ -f "$BK/20261106-phaseB/.done" ] || die "backup phases A and B not both complete"
( cd "$BK/20261106-phaseA" && sha256sum -c SHA256SUMS >/dev/null ) || die "phase A checksum"
( cd "$BK/20261106-phaseB" && sha256sum -c SHA256SUMS >/dev/null ) || die "phase B checksum"
for p in "$HH/hermes-agent" "$HH/hermes-agent.staged" "$WS/hermes-webui" "$WS/hermes-webui.staged"; do [ -d "$p" ] && [ ! -L "$p" ] || die "missing/symlink $p"; done
for p in "$HH/hermes-agent.pre-upgrade" "$WS/hermes-webui.pre-upgrade"; do [ ! -e "$p" ] || die "$p already exists"; done
mv "$HH/hermes-agent" "$HH/hermes-agent.pre-upgrade"
mv "$HH/hermes-agent.staged" "$HH/hermes-agent"
mv "$WS/hermes-webui" "$WS/hermes-webui.pre-upgrade"
mv "$WS/hermes-webui.staged" "$WS/hermes-webui"
echo SWAPPED-OK
