#!/usr/bin/env bash
# [[file:../../../../../sanctuary-cortex.org::*Agentify Cortex — host-side browser-session lane][Agentify Cortex — host-side browser-session lane:3]]
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "$0")/../../../../.." && pwd)"
LAUNCHER="$ROOT/linux/.local/bin/agentify-cortex"
tmp="$(mktemp -d)"
trap 'if [ -f "$tmp/fake.pid" ]; then kill "$(cat "$tmp/fake.pid")" 2>/dev/null || true; fi; rm -rf -- "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/home/.local/bin"
touch "$tmp/home/.Xauthority"
cat >"$tmp/home/.local/bin/sanctuary-cortex-xpra" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$FAKE_XPRA_START_MARKER"
touch "$FAKE_XPRA_READY"
EOF
cat >"$tmp/bin/xpra" <<'EOF'
#!/usr/bin/env bash
if [ -f "$FAKE_XPRA_READY" ]; then
  printf '%s\n' ':101'
else
  printf '%s\n' "${FAKE_XPRA_LIST:-:101}"
fi
EOF
cat >"$tmp/bin/gdbus" <<'EOF'
#!/usr/bin/env bash
[[ "$FAKE_DBUS_MODE" == good ]]
EOF
cat >"$tmp/bin/curl" <<'EOF'
#!/usr/bin/env bash
[[ "$FAKE_HEALTH_MODE" == good ]] || exit 22
sid="$(jq -r '.serverId' "$AGENTIFY_CORTEX_STATE")"
printf '{"ok":true,"serverId":"%s"}\n' "$sid"
EOF
cat >"$tmp/bin/dbus-run-session" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' private >"$FAKE_DBUS_MARKER"
shift
exec "$@"
EOF
cat >"$tmp/bin/agentify-desktop" <<'EOF'
#!/usr/bin/env bash
[[ "$AGENTIFY_DESKTOP_CHROME_BIN" == "$FAKE_CHROME_BIN" ]]
count=0
[ -f "$FAKE_LAUNCH_COUNT" ] && count="$(cat "$FAKE_LAUNCH_COUNT")"
printf '%s\n' "$((count + 1))" >"$FAKE_LAUNCH_COUNT"
printf '{"ok":true,"pid":%s,"port":43123,"serverId":"fresh-server","startedAt":"2026-09-12T00:00:00Z"}\n' "$FAKE_STATE_PID" >"$AGENTIFY_CORTEX_STATE"
sleep 1
EOF
printf '#!/usr/bin/env bash\nexit 0\n' >"$tmp/bin/fake-chrome"
chmod 755 "$tmp/bin/"* "$tmp/home/.local/bin/sanctuary-cortex-xpra"

run_launcher() {
  HOME="$tmp/home" PATH="$tmp/bin:$PATH" \
  AGENTIFY_CORTEX_STATE="$tmp/state.json" AGENTIFY_CORTEX_LOCK="$tmp/lock" \
  AGENTIFY_CORTEX_LOG="$tmp/agentify.log" AGENTIFY_CORTEX_XPRA_BIN="$tmp/bin/xpra" \
  AGENTIFY_CORTEX_CURL_BIN="$tmp/bin/curl" AGENTIFY_CORTEX_GDBUS_BIN="$tmp/bin/gdbus" \
  AGENTIFY_CORTEX_DBUS_RUN_SESSION_BIN="$tmp/bin/dbus-run-session" \
  AGENTIFY_CORTEX_DESKTOP_BIN="$tmp/bin/agentify-desktop" \
  AGENTIFY_CORTEX_CHROME_BIN="$tmp/bin/fake-chrome" FAKE_CHROME_BIN="$tmp/bin/fake-chrome" \
  FAKE_DBUS_MARKER="$tmp/dbus.marker" FAKE_LAUNCH_COUNT="$tmp/launches" \
  FAKE_XPRA_READY="$tmp/xpra.ready" FAKE_XPRA_START_MARKER="$tmp/xpra.start" \
  FAKE_STATE_PID="$$" \
  FAKE_DBUS_MODE="$TEST_DBUS_MODE" FAKE_HEALTH_MODE="$TEST_HEALTH_MODE" \
  FAKE_XPRA_LIST="${TEST_XPRA_LIST:-:101}" \
  "$LAUNCHER"
}

printf '%s\n' 0 >"$tmp/launches"
[[ "$(HOME="$tmp/home" "$LAUNCHER" --help)" == "Usage: agentify-cortex" ]]
touch "$tmp/run"
TEST_DBUS_MODE=bad TEST_HEALTH_MODE=good run_launcher
[[ "$(cat "$tmp/dbus.marker")" == private ]]
[[ "$(cat "$tmp/launches")" == 1 ]]
:

printf '%s\n' '{"pid":2147483647,"port":43123,"serverId":"stale","startedAt":"2026-08-25T00:00:00Z"}' >"$tmp/state.json"
TEST_DBUS_MODE=bad TEST_HEALTH_MODE=good run_launcher
[[ "$(cat "$tmp/launches")" == 2 ]]
:

printf '%s\n' "{\"ok\":true,\"pid\":$$,\"port\":43123,\"serverId\":\"healthy\",\"startedAt\":\"2026-09-12T00:00:00Z\"}" >"$tmp/state.json"
TEST_DBUS_MODE=good TEST_HEALTH_MODE=good run_launcher
[[ "$(cat "$tmp/launches")" == 2 ]]

rm -f "$tmp/state.json" "$tmp/xpra.ready" "$tmp/xpra.start"
TEST_DBUS_MODE=bad TEST_HEALTH_MODE=good TEST_XPRA_LIST=:1010 run_launcher
[[ "$(cat "$tmp/xpra.start")" == start-full ]]
[[ "$(cat "$tmp/launches")" == 3 ]]
:

printf '%s\n' '{"ok":true,"pid":2147483647,"port":43123,"serverId":"mcp-not-gui","startedAt":"2026-09-12T00:00:00Z"}' >"$tmp/state.json"
TEST_DBUS_MODE=good TEST_HEALTH_MODE=good run_launcher
[[ "$(cat "$tmp/launches")" == 4 ]]
! grep -q 'pgrep' "$LAUNCHER"
printf '%s\n' 'agentify-cortex lifecycle tests: ok'
# Agentify Cortex — host-side browser-session lane:3 ends here
