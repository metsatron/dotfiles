#!/usr/bin/env bash
# [[file:../../../../../sanctuary-cortex.org::*Agentify Cortex boot and liveness owner][Agentify Cortex boot and liveness owner:3]]
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "$0")/../../../../.." && pwd)"
SUPERVISOR="$ROOT/linux/.local/bin/agentify-cortex-supervise"
CRON_APPLY="$ROOT/linux/.local/bin/agentify-cortex-supervise-cron-apply"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/state"

cat >"$tmp/bin/hostname" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' kikin-kushi
EOF
cat >"$tmp/bin/agentify-cortex" <<'EOF'
#!/usr/bin/env bash
count=0
[ -f "$FAKE_COUNT" ] && count="$(cat "$FAKE_COUNT")"
count=$((count + 1))
printf '%s\n' "$count" >"$FAKE_COUNT"
[ -z "${FAKE_HOLD_SECONDS:-}" ] || sleep "$FAKE_HOLD_SECONDS"
[ "$count" -ge "${FAKE_SUCCEED_AT:-1}" ]
EOF
chmod 755 "$tmp/bin/hostname" "$tmp/bin/agentify-cortex"

FAKE_COUNT="$tmp/count" FAKE_SUCCEED_AT=2 \
AGENTIFY_CORTEX_SUPERVISE_HOSTNAME_BIN="$tmp/bin/hostname" \
"$SUPERVISOR" --expected-host kikin-kushi --attempts 3 --retry-seconds 0 \
  --launch-timeout 5 --launcher "$tmp/bin/agentify-cortex" --state-dir "$tmp/state"
[[ "$(cat "$tmp/count")" == 2 ]]
jq -e '.schema == "dotcortex.agentify-cortex-supervise.v1" and .status == "ready" and .attempt == 2' \
  "$tmp/state/receipt.json" >/dev/null

rm -f "$tmp/count"
FAKE_COUNT="$tmp/count" FAKE_SUCCEED_AT=1 FAKE_HOLD_SECONDS=1 \
AGENTIFY_CORTEX_SUPERVISE_HOSTNAME_BIN="$tmp/bin/hostname" \
"$SUPERVISOR" --expected-host kikin-kushi --attempts 1 --launch-timeout 5 \
  --launcher "$tmp/bin/agentify-cortex" --state-dir "$tmp/state.concurrent" &
owner_pid=$!
for _ in $(seq 1 50); do [ -s "$tmp/count" ] && break; sleep 0.02; done
locked_out="$(FAKE_COUNT="$tmp/count" FAKE_SUCCEED_AT=1 \
  AGENTIFY_CORTEX_SUPERVISE_HOSTNAME_BIN="$tmp/bin/hostname" \
  "$SUPERVISOR" --expected-host kikin-kushi --attempts 1 --launch-timeout 5 \
  --launcher "$tmp/bin/agentify-cortex" --state-dir "$tmp/state.concurrent")"
grep -Fq 'another supervisor owns the lock' <<<"$locked_out"
wait "$owner_pid"
[[ "$(cat "$tmp/count")" == 1 ]]

if AGENTIFY_CORTEX_SUPERVISE_HOSTNAME_BIN="$tmp/bin/hostname" \
  "$SUPERVISOR" --expected-host wrong-host --launcher "$tmp/bin/agentify-cortex" --state-dir "$tmp/state.bad"; then
  echo "wrong-host supervisor unexpectedly succeeded" >&2
  exit 1
fi

cron_out="$(HOME="$tmp/home" AGENTIFY_CORTEX_CRON_HOSTNAME_BIN="$tmp/bin/hostname" \
  "$CRON_APPLY" --host kikin-kushi --dry-run)"
grep -Fq '@reboot' <<<"$cron_out"
grep -Fq '*/2 * * * *' <<<"$cron_out"
grep -Fq 'agentify-cortex-supervise --expected-host kikin-kushi' <<<"$cron_out"

[[ "$("$SUPERVISOR" --help)" == Usage:* ]]
[[ "$("$CRON_APPLY" --help)" == Usage:* ]]
printf '%s\n' 'agentify-cortex supervision tests: ok'
# Agentify Cortex boot and liveness owner:3 ends here
