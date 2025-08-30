#!/usr/bin/env bash
set -euo pipefail

killall -q kdeconnectd 2>/dev/null || true
kdeconnect-cli --refresh

# Poll for up to ~10s until any paired+reachable device appears
for i in {1..20}; do
  if kdeconnect-cli --list-available | grep -q .; then
    break
  fi
  sleep 0.5
done

# Act on all devices once available
kdeconnect-cli -a || true
