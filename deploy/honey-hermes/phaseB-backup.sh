#!/bin/bash
# Root. Requires gateway+webui STOPPED. Opaque snapshot of ~/.hermes state (never read or printed).
set -euo pipefail; . "$(dirname "$0")/lib.sh"; svc_stopped
B=$BK/20261106-phaseB; [ ! -e "$B" ] || die "$B exists"
install -d -m 0700 -o root -g root "$B"
tar --zstd --numeric-owner --xattrs --acls -cpf "$B/hermes-home.tar.zst" -C "$(dirname "$HH")" \
  --exclude="$(basename "$HH")/hermes-agent" --exclude="$(basename "$HH")/hermes-agent.*" \
  --exclude="$(basename "$HH")/tools" --exclude="$(basename "$HH")/cache" --exclude="$(basename "$HH")/installs" --exclude="$(basename "$HH")/node" \
  --exclude="$(basename "$HH")/lsp" --exclude="$(basename "$HH")/logs" --exclude="$(basename "$HH")/backups" --exclude="$(basename "$HH")/chromium*" \
  "$(basename "$HH")"
( cd "$B" && sha256sum hermes-home.tar.zst > SHA256SUMS && sha256sum -c SHA256SUMS >/dev/null )
echo "entries: $(tar --zstd -tf "$B/hermes-home.tar.zst" | wc -l)  size: $(stat -c %s "$B/hermes-home.tar.zst")"
chmod 0600 "$B"/*; date -Is > "$B/.done"; echo PHASEB-OK
