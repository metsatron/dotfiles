#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../../.." && pwd)"
HELPER="$ROOT/linux/.local/bin/t480s-plank-apply"
MANIFEST="$ROOT/t480s/.config/dotcortex/plank-launchers.ssv"
DCONF_SOURCE="$ROOT/t480s/.config/plank/plank.dconf"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT

mkdir -p "$tmp/bin" "$tmp/home"
cat > "$tmp/bin/dconf" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "$DCONF_TEST_ARGS"
cat > "$DCONF_TEST_INPUT"
EOF
chmod 755 "$tmp/bin/dconf"

run_apply() {
  HOME="$tmp/home" \
  XDG_CONFIG_HOME="$tmp/config" \
  PLANK_LAUNCHER_MANIFEST="$MANIFEST" \
  PLANK_DCONF_SOURCE="$DCONF_SOURCE" \
  PLANK_CONFIG_HOME="$tmp/plank" \
  DCONF_BIN="$tmp/bin/dconf" \
  DBUS_SESSION_BUS_ADDRESS='unix:path=/tmp/dotcortex-test-bus' \
  DCONF_TEST_ARGS="$tmp/dconf.args" \
  DCONF_TEST_INPUT="$tmp/dconf.input" \
  "$HELPER"
}

run_apply
expected_count="$(awk 'NF && $1 !~ /^#/' "$MANIFEST" | wc -l)"
actual_count="$(find "$tmp/plank/dock1/launchers" -type f -name '*.dockitem' | wc -l)"
[[ "$actual_count" -eq "$expected_count" ]]
grep -Fx 'load /net/launchpad/plank/' "$tmp/dconf.args" >/dev/null
cmp -s "$DCONF_SOURCE" "$tmp/dconf.input"
grep -Fx "Launcher=file://$tmp/home/.local/share/applications/kitty.desktop" \
  "$tmp/plank/dock1/launchers/kitty.dockitem" >/dev/null
grep -Fx 'Launcher=docklet://trash' \
  "$tmp/plank/dock1/launchers/trash.dockitem" >/dev/null

before="$tmp/before.sha256"
after="$tmp/after.sha256"
find "$tmp/plank/dock1/launchers" -type f -print0 | sort -z | xargs -0 sha256sum > "$before"
run_apply
find "$tmp/plank/dock1/launchers" -type f -print0 | sort -z | xargs -0 sha256sum > "$after"
cmp -s "$before" "$after"

bad_dconf="$tmp/bad.dconf"
sed "s/, 'trash.dockitem'//" "$DCONF_SOURCE" > "$bad_dconf"
if HOME="$tmp/home" XDG_CONFIG_HOME="$tmp/bad-config" \
  PLANK_LAUNCHER_MANIFEST="$MANIFEST" PLANK_DCONF_SOURCE="$bad_dconf" \
  PLANK_CONFIG_HOME="$tmp/bad-plank" DCONF_BIN="$tmp/bin/dconf" \
  DBUS_SESSION_BUS_ADDRESS='unix:path=/tmp/dotcortex-test-bus' \
  DCONF_TEST_ARGS="$tmp/bad.args" DCONF_TEST_INPUT="$tmp/bad.input" \
  "$HELPER" >/dev/null 2>&1; then
  echo 't480s-plank-apply test: mismatched order unexpectedly succeeded' >&2
  exit 1
fi
[[ ! -e "$tmp/bad-plank/dock1/launchers" ]]

printf '%s\n' 't480s-plank-apply test: ok'
