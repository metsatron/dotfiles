#!/bin/bash
# Phase A: hot, code-only backup of Hermes + WebUI + OpenRC scripts + the hermes launcher. No config/auth/state db/logs. Root.
set -euo pipefail; . "$(dirname "$0")/lib.sh"
B=$BK/20261106-phaseA; [ ! -e "$B" ] || die "$B exists"
install -d -m 0700 -o root -g root /var/lib/hermes-upgrade "$BK" "$B"
H=$HH/hermes-agent; W=$WS/hermes-webui
{ echo "hermes_head=$(git -C "$H" rev-parse HEAD)"; echo "hermes_status_entries=$(git -C "$H" status --short | wc -l)"
  echo "webui_head=$(git -C "$W" rev-parse HEAD)"; echo "webui_status_entries=$(git -C "$W" status --short | wc -l)"; echo "taken=$(date -Is)"; } > "$B/revisions.txt"
git -C "$H" diff HEAD > "$B/hermes-working-tree.diff" || true; git -C "$W" diff HEAD > "$B/webui-working-tree.diff" || true
"$H/venv/bin/python3" -m pip freeze > "$B/hermes-venv-freeze.txt" 2>/dev/null || true
cp -a "$INITD/hermes-gateway" "$INITD/hermes-webui" "$B/"
# The target rewrites this launcher at first start; keep the original text so rollback can put it back.
cp -a "$LB/hermes" "$B/hermes-wrapper.orig"
tar --zstd --numeric-owner --xattrs --acls -cpf "$B/hermes-agent.tar.zst" -C "$(dirname "$H")" "$(basename "$H")"
tar --zstd --numeric-owner --xattrs --acls -cpf "$B/hermes-webui.tar.zst" -C "$(dirname "$W")" "$(basename "$W")"
( cd "$B" && sha256sum hermes-agent.tar.zst hermes-webui.tar.zst hermes-gateway hermes-webui hermes-wrapper.orig revisions.txt ./*.diff hermes-venv-freeze.txt > SHA256SUMS )
chmod 0600 "$B"/*; date -Is > "$B/.done"; echo PHASEA-OK
