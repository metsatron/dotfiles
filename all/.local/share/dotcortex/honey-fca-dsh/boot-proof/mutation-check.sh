#!/usr/bin/env bash
# Mutation proof for the revision-7 boot/telemetry tests: each sabotaged lane MUST fail test_boot_profile.py. Disposable space only.
set -uo pipefail
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
mutate() { # name file perl-expression (-0pi: whole-file, multi-line capable); the file is a standalone product next to this script
  local name="$1" file="$2" expr="$3" d="$TMP/$1"
  mkdir -p "$d"; cp "$HERE"/honey-fca-dsh "$HERE"/cordis.patch.yml "$HERE"/boot_check.mjs "$HERE"/SOURCE.md "$HERE"/test_boot_profile.py "$d"/
  perl -0pi -e "$expr" "$d/$file"
  if cmp -s "$HERE/$file" "$d/$file"; then echo "MUTATION NOT APPLIED: $name"; fail=1; return; fi
  if python3 -B "$d/test_boot_profile.py" >"$d/out" 2>&1; then echo "SURVIVED (tests too weak): $name"; fail=1
  else echo "killed: $name ($(grep -c '^FAIL\|^ERROR' "$d/out") failing)"; fi
}
mutate telemetry-row-removed       cordis.patch.yml 's/- id: session-telemetry-otel\n  disabled: true\n//'
mutate telemetry-row-enabled       cordis.patch.yml 's/(- id: session-telemetry-otel\n  disabled: )true/${1}false/'
mutate telemetry-env-removed       honey-fca-dsh    's/ DSH_TELEMETRY_DISABLED=1//'
mutate telemetry-env-empty         honey-fca-dsh    's/DSH_TELEMETRY_DISABLED=1/DSH_TELEMETRY_DISABLED=/'
mutate boot-row-removed            cordis.patch.yml 's/- id: spill-policy\n  disabled: true\n//'
mutate probe-uses-own-env          honey-fca-dsh    's/(if \[ "\$ACTION" = probe \]; then\n  exec "\$BWRAP" "\$\{common\[@\]\}" \/usr\/bin\/env -i )"\$\{WORKER_ENV\[@\]\}"/${1}PATH=\/usr\/bin HOME=\/tmp\/worker-home DSH_HOME=\/tmp\/dsh-home/'
mutate boot-check-inherits-env     honey-fca-dsh    's/(= boot-check \]; then\n.*\n  exec "\$BWRAP" "\$\{common\[@\]\}" \/usr\/bin\/env) -i/${1}/'
mutate boot-check-never-fails      boot_check.mjs   's/(report\(.failed., \{ detail \}\);\n  process\.exit\()1/${1}0/'
mutate boot-check-reports-ok-unbooted boot_check.mjs 's/await runCli\(\);/await Promise.resolve();/'
mutate listing-hides-writes        boot_check.mjs   's/dsh_home: files\(process\.env\.DSH_HOME\)/dsh_home: []/'
exit $fail
