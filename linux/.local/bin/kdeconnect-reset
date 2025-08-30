#!/usr/bin/env bash
set -euo pipefail

killall -q kdeconnectd 2>/dev/null || true
kdeconnect-cli --refresh

# Poll for up to ~10s until a device appears as available
for i in {1..20}; do
  if kdeconnect-cli --list-available | grep -q .; then
    break
  fi
  sleep 0.5
done

kdeconnect-cli -a