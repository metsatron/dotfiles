#!/usr/bin/bash -p
# Least-privilege change for the sterile FCA worker: remove ONLY agent-deepseek's supplementary cortex membership. Touches no other
# user or group. Default is a dry run that prints the plan; --apply and --rollback need root and a human release (not run by this
# candidate). The worker owns its runtime/fixture (test-identity-nocortex.sh proves the lane runs without cortex); cortex would
# otherwise give it traverse access to the sealed operator home. A re-run of agent-users-bootstrap re-adds cortex (see ROLLOUT).
set -euo pipefail
PATH=/usr/sbin:/usr/bin:/sbin:/bin; export PATH
USER_NAME=agent-deepseek; GROUP_NAME=cortex; WANT_UID=2012
MODE="${1:-dry-run}"; [ "$#" -le 1 ] || { echo 'refused: one optional argument' >&2; exit 2; }
case "$MODE" in dry-run|--apply|--rollback) ;; *) echo 'usage: cortex-removal.sh [--apply|--rollback]' >&2; exit 2 ;; esac
[ "$(/usr/bin/id -u "$USER_NAME")" = "$WANT_UID" ] || { echo "refused: $USER_NAME is not uid $WANT_UID" >&2; exit 3; }
members() { /usr/bin/getent group "$GROUP_NAME" | /usr/bin/cut -d: -f4; }
groups_of() { /usr/bin/id -nG "$USER_NAME" | /usr/bin/tr ' ' '\n' | /usr/bin/sort | /usr/bin/paste -sd,; }
echo "before: $USER_NAME groups=$(groups_of); $GROUP_NAME members=$(members)"
before_members="$(members)"
case "$MODE" in
  dry-run)  echo "plan: /usr/bin/gpasswd -d $USER_NAME $GROUP_NAME    (rollback: /usr/bin/gpasswd -a $USER_NAME $GROUP_NAME)"; exit 0 ;;
  --apply)    [ "$(/usr/bin/id -u)" = 0 ] || { echo 'refused: run as root' >&2; exit 3; }
              /usr/bin/gpasswd -d "$USER_NAME" "$GROUP_NAME"
              want="$(printf '%s' "$before_members" | /usr/bin/tr ',' '\n' | /usr/bin/grep -vx "$USER_NAME" | /usr/bin/paste -sd,)" ;;
  --rollback) [ "$(/usr/bin/id -u)" = 0 ] || { echo 'refused: run as root' >&2; exit 3; }
              /usr/bin/gpasswd -a "$USER_NAME" "$GROUP_NAME"
              want="$before_members,$USER_NAME"; want="${want#,}" ;;
esac
after="$(members)"
echo "after:  $USER_NAME groups=$(groups_of); $GROUP_NAME members=$after"
# Every other member must be untouched (order-insensitive); the target is the only difference.
[ "$(printf '%s' "$after" | /usr/bin/tr ',' '\n' | /usr/bin/sort | /usr/bin/paste -sd,)" = "$(printf '%s' "$want" | /usr/bin/tr ',' '\n' | /usr/bin/sort | /usr/bin/paste -sd,)" ] || { echo 'FAILED: membership differs from the expected set' >&2; exit 4; }
[ "$MODE" = --rollback ] || ! /usr/bin/id -nG "$USER_NAME" | /usr/bin/tr ' ' '\n' | /usr/bin/grep -qx "$GROUP_NAME" || { echo 'FAILED: still a member' >&2; exit 4; }
echo "ok"
