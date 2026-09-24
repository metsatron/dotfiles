#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../../.." && pwd)"
GATE="$ROOT/debian/.local/bin/brave-canary-gate"
tmp="$(mktemp -d)"
trap 'find "$tmp" -depth -delete 2>/dev/null || true' EXIT
policy="$tmp/policy"; state="$tmp/state"; actions="$tmp/actions"; profile="$tmp/real-profile"
printf '%s\n' 'known_good 1.92.143' 'rejected 1.95.101' > "$policy"
mkdir "$profile"; printf '%s\n' untouched > "$profile/sentinel"; before="$(sha256sum "$profile/sentinel")"

run_gate() {
  : > "$actions"
  BRAVE_GATE_TEST=1 BRAVE_POLICY="$policy" BRAVE_STATE="$state" BRAVE_GATE_TEST_ACTIONS="$actions" \
    BRAVE_GATE_TEST_CANDIDATE="$1" BRAVE_GATE_TEST_CANARY="${2:-fail}" BRAVE_GATE_TEST_INSTALLED=1.92.143 \
    "$GATE" >/dev/null
}

run_gate 1.95.101 pass
grep -qx hold "$actions"
run_gate 1.96.0 fail
grep -qx 'rollback 1.92.143' "$actions"
grep -qx hold "$actions"
grep -qx 'rejected 1.96.0' <(awk '$1 == "rejected" {print $1, $2}' "$state")
run_gate 1.96.0 pass
if grep -qx 'approve 1.96.0' "$actions"; then
  echo 'known-bad candidate was re-canaried' >&2
  exit 1
fi
run_gate 1.97.0 pass
grep -qx 'approve 1.97.0' "$actions"
grep -qx 'known_good 1.97.0' <(awk '$1 == "known_good" {print $1, $2}' "$state")
[ "$(sha256sum "$profile/sentinel")" = "$before" ]
grep -q '\[ "$pkg" = brave-browser \] && continue' "$ROOT/debian/.local/bin/nala-apply"
printf '%s\n' 'brave canary gate fixtures: ok'
