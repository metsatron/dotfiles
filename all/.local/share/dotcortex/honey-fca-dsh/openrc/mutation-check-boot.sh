#!/usr/bin/env bash
# Mutation proof for the relay's OpenRC unit and installer: each sabotaged copy MUST fail the suite, by a NAMED unittest failure.
# A pass, a stall, a skip or a REFUSAL is never a kill. A mutant only a RealOpenRC test can kill is reported UNPROVEN (exit 3) unless those tests
# ran on a declared-disposable OpenRC host; it is never counted as killed. Exit 0 = every mutant killed, 1 = a survivor or an error, 3 = unproven only.
# Disposable space only; the candidate is not modified. Do NOT set HONEY_DISPOSABLE_OPENRC_HOST on a host that carries services.
set -uo pipefail
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
LANE="$(dirname "$HERE")"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0; killed=0; unproven=0
mutate() { # name file sed-expression
  local name="$1" file="$2" expr="$3" d="$TMP/$1" out rc names
  mkdir -p "$d"; cp -r "$LANE/egress" "$LANE/openrc" "$d"/
  sed -i "$expr" "$d/openrc/$file"
  if cmp -s "$HERE/$file" "$d/openrc/$file"; then echo "MUTATION NOT APPLIED: $name"; fail=1; return; fi
  out="$(timeout 300 python3 "$d/openrc/test_honey_fca_egress.py" 2>&1)"; rc=$?
  if [ "$rc" = 124 ]; then echo "TIMEOUT (infrastructure, NOT a kill): $name [$file]"; fail=1; return; fi
  if ! printf '%s\n' "$out" | grep -qE '^(FAILED \(|OK)'; then
    echo "INFRASTRUCTURE ERROR (not a kill): $name [$file]"; printf '%s\n' "$out" | tail -8 | sed 's/^/    | /'; fail=1; return; fi
  # Evidence of a kill = a named failure OTHER than the RealOpenRC tests when those REFUSED (they refuse on any host that has not been declared
  # disposable, and a refusal fails every mutant alike, so it proves nothing). A skip proves nothing either.
  names="$(printf '%s\n' "$out" | grep -E '^(FAIL|ERROR):' )"
  if printf '%s\n' "$out" | grep -q 'REFUSED:'; then names="$(printf '%s\n' "$names" | grep -v 'RealOpenRC')"; fi
  names="$(printf '%s\n' "$names" | sed 's/^[A-Z]*: //; s/ (.*//' | sed '/^$/d' | head -3 | tr '\n' ' ')"
  if [ -n "$names" ]; then killed=$((killed+1)); echo "killed: $name [$file] by: $names"
  elif [ "$rc" != 0 ] || printf '%s\n' "$out" | grep -qE 'skipped=|REFUSED:'; then
    unproven=$((unproven+1)); echo "UNPROVEN (only a RealOpenRC test could kill it, and those did not run here; needs a disposable OpenRC host): $name [$file]"
  else echo "SURVIVED (tests too weak): $name [$file]"; fail=1; fi
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
mutate start-post-never-fails        $B "/^    stop >\/dev\/null 2>&1\$/{n;s/return 1/return 0/}"
mutate start-post-leaves-relay-up    $B "/^    stop >\/dev\/null 2>&1\$/d"
mutate start-post-skips-socket-wait  $B "s/\[ -S \"\${run_dir}\/relay.sock\" \] \&\& return 0/true \&\& return 0/"
mutate stop-post-removes-run-dir     $B "s|rm -f \"\${run_dir}/relay.sock\"|rm -rf \"\${run_dir}\"|"
mutate no-acl-for-worker             $B "/setfacl -m/d"
mutate log-world-readable            $B "s/checkpath -f -m 0640/checkpath -f -m 0644/"
mutate stop-passes-exec              $B "s|--user \"\${relay_user}\" --pidfile|--user \"\${relay_user}\" --exec /usr/bin/python3 --pidfile|"
mutate stop-without-liveness-guard   $B "s|if \[ ! -d \"/proc/\${pid}\" \]; then|if false; then|"
mutate stop-without-empty-guard      $B "/\[ -n \"\${pid}\" \] || return 0/d"
mutate stop-without-user-filter      $B "s| --user \"\${relay_user}\" --pidfile| --pidfile|"
mutate start-post-uses-raw-ssd       $B "s|^    stop >/dev/null 2>&1\$|    start-stop-daemon --stop --quiet --pidfile \"\${pidfile}\" >/dev/null 2>\&1|"
echo "mutants: $killed killed, $unproven UNPROVEN, survivors/errors counted in the exit status"
[ "$fail" = 0 ] || exit 1
[ "$unproven" = 0 ] || exit 3
exit 0
