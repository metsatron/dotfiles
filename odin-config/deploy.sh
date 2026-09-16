#!/usr/bin/env bash
# Deploy the Odin RetroArch configuration


# [[file:../odin.org::*Deploy the Odin RetroArch configuration][Deploy the Odin RetroArch configuration:1]]
set -euo pipefail

TARGET_PKG="com.retroarch.aarch64"
ADB="${ADB:-$HOME/.guix-extra-profiles/dev/dev/bin/adb}"
DRY_RUN=0

case "${1:-}" in
  "") ;;
  --dry-run) DRY_RUN=1 ;;
  --help|-h)
    echo "usage: $(basename "$0") [--dry-run]"
    exit 0
    ;;
  *)
    echo "usage: $(basename "$0") [--dry-run]" >&2
    exit 2
    ;;
esac

if [ ! -x "$ADB" ]; then
  if PATH_ADB="$(command -v adb 2>/dev/null)" && [ -x "$PATH_ADB" ]; then
    ADB="$PATH_ADB"
  else
    echo "odin: adb not found or not executable (checked $ADB and PATH)" >&2
    exit 1
  fi
fi

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_DATA_DIR="/sdcard/Android/data/${TARGET_PKG}/files"
REMOTE_CONFIG_DIR="/sdcard/RetroArch/config"

print_cmd() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
}

run_adb() {
  print_cmd "$@"
  if (( DRY_RUN == 0 )); then
    "$@"
  fi
}

echo "Using adb: $ADB"
if (( DRY_RUN == 1 )); then
  echo "Dry run: skipping authorized-device check"
  print_cmd "$ADB" get-state
else
  echo "Checking for an authorized device"
  print_cmd "$ADB" get-state
  state="$("$ADB" get-state 2>/dev/null || true)"
  if [ "$state" != "device" ]; then
    echo "odin: no authorized device" >&2
    exit 1
  fi
  echo "Authorized device: device"
fi

echo "Ensuring remote RetroArch config directories"
run_adb "$ADB" shell mkdir -p "$REMOTE_DATA_DIR" "$REMOTE_CONFIG_DIR"

echo "Pushing RetroArch main config"
run_adb "$ADB" push "$SRC/retroarch.cfg" "$REMOTE_DATA_DIR/retroarch.cfg"

echo "Pushing RetroArch per-core overrides"
run_adb "$ADB" push "$SRC/shared/config/." "$REMOTE_CONFIG_DIR/"

if (( DRY_RUN == 1 )); then
  echo "Dry run complete: Odin Lite RetroArch config commands printed; no device changes made."
else
  echo "Success: Odin Lite RetroArch config deployed for ${TARGET_PKG} (config only)."
fi
# Deploy the Odin RetroArch configuration:1 ends here
