#!/usr/bin/env bash
# Proof that the worker needs no cortex membership: run the REAL tangled launcher as uid 2012 with NO supplementary groups
# (exactly the state after `gpasswd -d agent-deepseek cortex`) without changing any user or group. The lane is deployed to a
# worker-readable system path (a copy in /tmp here); from the sealed operator home it is unreachable without cortex, which is why
# the deployed lane must not live under /home/gille. Production launcher pin stays REVIEW_REQUIRED; only the /tmp copy is pinned.
set -euo pipefail
LANE_SRC="${1:-/home/gille/DotCortex/all/.local/share/dotcortex/honey-fca-dsh}"
STAGE=/home/agent-deepseek/.local/share/fca-dsh-runtime
TMP="$(mktemp -d /tmp/fca-lane-nocortex.XXXXXX)"; trap 'sudo -n rm -rf "$TMP"' EXIT
chmod 755 "$TMP"; cp -a "$LANE_SRC" "$TMP/lane"; chmod -R a+rX "$TMP/lane"
pin="$(sudo -n sha256sum "$STAGE/dsh/REVIEWED-CLOSURE.sha256" | cut -d' ' -f1)"
sed -i "s/^REVIEWED_CLOSURE_MANIFEST_SHA256=REVIEW_REQUIRED/REVIEWED_CLOSURE_MANIFEST_SHA256=$pin/" "$TMP/lane/bin/honey-fca-dsh"
as_worker() { local groups="$1" g=(--clear-groups); shift; [ -z "$groups" ] || g=(--groups "$groups")
  sudo -n setpriv --reuid=2012 --regid=2012 "${g[@]}" /usr/bin/env -i HOME=/home/agent-deepseek PATH=/usr/bin:/bin "$@"; }
echo "--- identity seen by the worker with no supplementary groups"
as_worker '' /usr/bin/id
[ "$(as_worker '' /usr/bin/id -G)" = 2012 ]
echo "--- cortex-owned files inside the worker home (none means nothing is stranded by removal)"
[ -z "$(sudo -n find /home/agent-deepseek -group cortex -print -quit)" ] && echo none
echo "--- offline probe and dsh-config from the worker-readable deployed copy, NO groups"
as_worker '' "$TMP/lane/bin/honey-fca-dsh" probe
as_worker '' "$TMP/lane/bin/honey-fca-dsh" dsh-config >"$TMP/cfg.out" 2>"$TMP/cfg.err"; echo "dsh-config exit=$? lines=$(wc -l <"$TMP/cfg.out") stderr_bytes=$(wc -c <"$TMP/cfg.err")"
[ ! -s "$TMP/cfg.err" ]
echo "--- same result WITH cortex (current state), so removal changes nothing for the lane"
a="$(as_worker '' "$TMP/lane/bin/honey-fca-dsh" probe)"; b="$(as_worker 2000 "$TMP/lane/bin/honey-fca-dsh" probe)"; [ "$a" = "$b" ] && echo identical
echo "--- the sealed operator home is NOT reachable without cortex (deploy the lane outside /home/gille)"
if as_worker '' /usr/bin/ls /home/gille/DotCortex >/dev/null 2>&1; then echo 'UNEXPECTED: reachable without cortex'; exit 1; else echo 'refused without cortex (EACCES)'; fi
as_worker 2000 /usr/bin/ls /home/gille/DotCortex >/dev/null 2>&1 && echo 'reachable with cortex: this is the access removal takes away'
