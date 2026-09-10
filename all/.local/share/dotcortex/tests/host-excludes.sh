#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../../.." && pwd)"
HELPER="$ROOT/all/.local/bin/host-excludes"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# --- Default-empty passthrough: missing manifest excludes nothing ---
missing="$tmp/missing.ssv"
if HOST_EXCLUDES="$missing" HOST_EXCLUDES_HOSTNAME=anyhost "$HELPER" nala gparted; then
  echo "missing-file check-form: expected exit 1 (not excluded), got 0" >&2
  exit 1
fi
out="$(HOST_EXCLUDES="$missing" HOST_EXCLUDES_HOSTNAME=anyhost "$HELPER" nala)"
if [ -n "$out" ]; then
  echo "missing-file list-form: expected empty output, got: $out" >&2
  exit 1
fi

# --- Fixture manifest ---
ssv="$tmp/host-excludes.ssv"
cat >"$ssv" <<'EOF'
# HOST LANE ID NOTE
kikin-kushi nala gparted "headless: no display"
kikin-kushi appimage Azahar "3DS emu won't run meaningfully"
kikin-kushi guix room-gaming "won't run heavy games on kikin"
EOF

# --- Host match + lane match + id match: excluded ---
if ! HOST_EXCLUDES="$ssv" HOST_EXCLUDES_HOSTNAME=kikin-kushi "$HELPER" nala gparted; then
  echo "exact match: expected exit 0 (excluded), got nonzero" >&2
  exit 1
fi
if ! HOST_EXCLUDES="$ssv" HOST_EXCLUDES_HOSTNAME=kikin-kushi "$HELPER" appimage Azahar; then
  echo "appimage match: expected exit 0 (excluded), got nonzero" >&2
  exit 1
fi
if ! HOST_EXCLUDES="$ssv" HOST_EXCLUDES_HOSTNAME=kikin-kushi "$HELPER" guix room-gaming; then
  echo "guix match: expected exit 0 (excluded), got nonzero" >&2
  exit 1
fi

# --- List-form for host+lane ---
out="$(HOST_EXCLUDES="$ssv" HOST_EXCLUDES_HOSTNAME=kikin-kushi "$HELPER" nala)"
[ "$out" = "gparted" ] || { echo "list-form: expected 'gparted', got: $out" >&2; exit 1; }

# --- Non-match: wrong host ---
if HOST_EXCLUDES="$ssv" HOST_EXCLUDES_HOSTNAME=t480 "$HELPER" nala gparted; then
  echo "wrong-host: expected exit 1 (not excluded), got 0" >&2
  exit 1
fi

# --- Non-match: wrong lane ---
if HOST_EXCLUDES="$ssv" HOST_EXCLUDES_HOSTNAME=kikin-kushi "$HELPER" appimage gparted; then
  echo "wrong-lane: expected exit 1 (not excluded), got 0" >&2
  exit 1
fi

# --- Non-match: wrong id ---
if HOST_EXCLUDES="$ssv" HOST_EXCLUDES_HOSTNAME=kikin-kushi "$HELPER" nala audacity; then
  echo "wrong-id: expected exit 1 (not excluded), got 0" >&2
  exit 1
fi

printf '%s\n' 'host-excludes fixtures: ok'
