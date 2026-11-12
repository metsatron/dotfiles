#!/usr/bin/env bash
# Mutation proof for the relay's OpenRC unit and installer: each sabotaged copy MUST fail the suite, by a NAMED unittest failure.
# A pass, a stall or a skipped run is an error, not a kill. Disposable space only; the candidate is not modified.
set -uo pipefail
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
LANE="$(dirname "$HERE")"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
mutate() { # name file sed-expression
  local name="$1" file="$2" expr="$3" d="$TMP/$1" out rc names
  mkdir -p "$d"; cp -r "$LANE/egress" "$LANE/openrc" "$d"/
  sed -i "$expr" "$d/openrc/$file"
  if cmp -s "$HERE/$file" "$d/openrc/$file"; then echo "MUTATION NOT APPLIED: $name"; fail=1; return; fi
  out="$(timeout 300 python3 "$d/openrc/test_honey_fca_egress.py" 2>&1)"; rc=$?
  if [ "$rc" = 0 ]; then echo "SURVIVED (tests too weak, or the run skipped): $name [$file]"; fail=1
  elif [ "$rc" = 124 ]; then echo "TIMEOUT (infrastructure, NOT a kill): $name [$file]"; fail=1
  elif printf '%s\n' "$out" | grep -qE '^FAILED \('; then
    names="$(printf '%s\n' "$out" | grep -E '^(FAIL|ERROR):' | sed 's/^[A-Z]*: //; s/ (.*//' | head -3 | tr '\n' ' ')"
    echo "killed: $name [$file] by: $names"
  else echo "INFRASTRUCTURE ERROR (not a kill): $name [$file]"; printf '%s\n' "$out" | tail -8 | sed 's/^/    | /'; fail=1; fi
}
B=honey-fca-egress I=honey-fca-egress-install
mutate runs-as-root              $B "s/^command_user=.*/command_user=\"root:root\"/"
mutate extra-relay-argument      $B "s|^command_args=\"-I \(.*\)\"|command_args=\"-I \1 --upstream example.com\"|"
mutate no-uid0-check             $B "s/\[ \"\$(id -u \"\${relay_user}\")\" -ne 0 \] ||/true ||/"
mutate no-supplementary-check    $B "s/\[ \"\$(id -G \"\${relay_user}\")\" = \"\$(id -g \"\${relay_user}\")\" \] ||/true ||/"
mutate no-worker-uid-check       $B "s/\[ \"\$(id -u \"\${worker_user}\" 2>\/dev\/null)\" = \"\${worker_uid}\" \] ||/true ||/"
mutate no-relay-file-check       $B "s/\[ -f \"\${relay_root}\/fca_egress_relay.py\" \] ||/true ||/"
mutate no-root-owned-check       $B "s/\\\\( ! -user root -o -perm \/022 \\\\)/-name no-such-file/"
mutate socket-dir-world-open     $B "s/checkpath -d -m 0700/checkpath -d -m 0755/"
mutate acl-grants-write          $B "s/u:\${worker_uid}:--x/u:\${worker_uid}:rwx/"
mutate hash-not-compared         $I "s/\[ \"\$got\" = \"\$EXPECT\" \] ||/true ||/"
mutate hash-optional             $I "s/^        \"\") problems+=(.*/        \"\") ;;/"
mutate installer-starts-service  $I "s/^    echo \"not started and not enabled.*/&\n    run rc-service honey-fca-egress start/"
mutate enable-links-wrong-unit   $I "s|ln -sfn ../init.d/honey-fca-egress|ln -sfn ../init.d/something-else|"
mutate no-backup-of-drifted-file $I "s/\[ -e \"\$d\" \] \&\& run cp -p \"\$d\" \"\$d.bak-\$ts\"/true/"
exit $fail
