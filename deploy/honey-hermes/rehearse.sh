#!/bin/bash
set -u
R=/tmp/hermes-rehearsal
rm -rf $R; mkdir -p $R/home/.hermes/{hermes-agent,hermes-agent.staged,logs,skills} $R/src/{hermes-webui,hermes-webui.staged} $R/backups/20261106-phaseA $R/bin $R/lb $R/initd
echo OLD > $R/home/.hermes/hermes-agent/VERSION; echo NEW > $R/home/.hermes/hermes-agent.staged/VERSION
echo OLDW > $R/src/hermes-webui/V; echo NEWW > $R/src/hermes-webui.staged/V
echo state-v1 > $R/home/.hermes/state.db; echo cfg-v1 > $R/home/.hermes/config.yaml; echo logx > $R/home/.hermes/logs/x
echo ok > $R/backups/20261106-phaseA/f; (cd $R/backups/20261106-phaseA && sha256sum f > SHA256SUMS && touch .done)
printf '#!/bin/bash\necho " * status: ${MOCK_STATE:-stopped}"\n' > $R/bin/rcmock; chmod +x $R/bin/rcmock
echo ORIGWRAP > $R/lb/hermes; cp $R/lb/hermes $R/backups/20261106-phaseA/hermes-wrapper.orig
for s in hermes-gateway hermes-webui; do printf '#!/sbin/openrc-run\nexport HOME=/h\n' > $R/initd/$s; cp $R/initd/$s $R/backups/20261106-phaseA/$s; done
export HH=$R/home/.hermes WS=$R/src BK=$R/backups RC=$R/bin/rcmock SKIP_PROC_CHECK=1 LB=$R/lb INITD=$R/initd OWNER=$(id -un)
D=$(cd "$(dirname "$0")" && pwd)
echo "--- 1 refuses when started"; MOCK_STATE=started $D/phaseB-backup.sh 2>&1 | tail -1
echo "--- 2 phase B"; $D/phaseB-backup.sh 2>&1 | tail -2
echo "--- 3 go-live"; $D/go-live.sh 2>&1 | tail -1; echo "  agent=$(cat $R/home/.hermes/hermes-agent/VERSION) webui=$(cat $R/src/hermes-webui/V) dirs=$(ls $R/home/.hermes | tr '\n' ' ')"
echo "--- 3a launchers (twice = idempotent)"; $D/hermes-launchers | tail -1; $D/hermes-launchers | tail -1; echo "  wrapper-has-env=$(grep -c HERMES_DISABLE_LAZY_INSTALLS $R/lb/hermes) init-exports=$(grep -c "^export HERMES_DISABLE_LAZY_INSTALLS" $R/initd/hermes-gateway $R/initd/hermes-webui | tr '\n' ' ')"
echo "--- 3b go-live refuses second run"; $D/go-live.sh 2>&1 | tail -1
echo "--- 4 migrate state then rollback --restore-state"; echo state-v2-MIGRATED > $R/home/.hermes/state.db; echo cfg-v2 > $R/home/.hermes/config.yaml
$D/rollback.sh --restore-state 2>&1 | tail -2
echo "  agent=$(cat $R/home/.hermes/hermes-agent/VERSION) webui=$(cat $R/src/hermes-webui/V) state=$(cat $R/home/.hermes/state.db) cfg=$(cat $R/home/.hermes/config.yaml) dirs=$(ls $R/home/.hermes | tr '\n' ' ')"
echo "  wrapper-after-rollback=$(cat $R/lb/hermes) init-has-env=$(grep -c HERMES_DISABLE $R/initd/hermes-gateway)"
echo "--- 5 rollback refuses when started"; MOCK_STATE=started $D/rollback.sh 2>&1 | tail -1
