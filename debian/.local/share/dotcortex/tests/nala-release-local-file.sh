#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../../.." && pwd)"
HELPER="$ROOT/debian/.local/bin/nala-release-sync"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
printf '%s\n' 'ID=ubuntu' 'VERSION_ID="24.04"' > "$tmp/os-release"
touch "$tmp/no-devuan"

stubbin="$tmp/bin"
mkdir -p "$stubbin" "$tmp/home" "$tmp/builds" "$tmp/elsewhere"
printf '%s\n' '#!/usr/bin/env bash' '[ "${1:-}" = --print-architecture ] && { printf "amd64\n"; exit 0; }' 'exit 2' > "$stubbin/dpkg"
printf '%s\n' '#!/usr/bin/env bash' 'case "${3:-}" in Package) printf "%s" "${NALA_TEST_DEB_PKG:-caddy}";; Version) printf "%s" "${NALA_TEST_DEB_VER:-0.1.0}";; Architecture) printf "%s" "${NALA_TEST_DEB_ARCH:-amd64}";; *) exit 2;; esac' > "$stubbin/dpkg-deb"
printf '%s\n' '#!/usr/bin/env bash' 'if [ ! -f "${NALA_TEST_STATE:-}" ]; then exit 1; fi' 'IFS=$'"'"'\t'"'"' read -r s v < "$NALA_TEST_STATE"' 'case "${2:-}" in *Status*) printf "%s\t%s\n" "$s" "$v";; *) printf "%s\n" "$v";; esac' > "$stubbin/dpkg-query"
printf '%s\n' '#!/usr/bin/env bash' 'while [[ "${1:-}" == *=* ]]; do export "$1"; shift; done' 'exec "$@"' > "$stubbin/sudo"
printf '%s\n' '#!/usr/bin/env bash' 'printf "apt-get:%s\n" "$*" >> "$NALA_TEST_LOG"' 'if [ "${NALA_TEST_REPAIR:-0}" = 1 ] && [ -n "${NALA_TEST_STATE:-}" ]; then printf "install ok installed\t0.1.0\n" > "$NALA_TEST_STATE"; fi' 'exit 0' > "$stubbin/apt-get"
printf '%s\n' '#!/usr/bin/env bash' 'printf "nala:%s\n" "$*" >> "$NALA_TEST_LOG"' 'if [ "${NALA_TEST_REPAIR:-0}" = 1 ] && [ -n "${NALA_TEST_STATE:-}" ]; then printf "install ok installed\t0.1.0\n" > "$NALA_TEST_STATE"; fi' 'exit 0' > "$stubbin/nala"
printf '%s\n' '#!/usr/bin/env bash' 'printf curl-called >> "$NALA_TEST_LOG"; exit 2' > "$stubbin/curl"
chmod +x "$stubbin"/*

printf 'fixture-deb\n' > "$tmp/builds/Caddy_0.1.0_amd64.deb"
printf 'escape-deb\n' > "$tmp/elsewhere/escape.deb"
ln -s "$tmp/builds/Caddy_0.1.0_amd64.deb" "$tmp/builds/link.deb"
sha="$(sha256sum "$tmp/builds/Caddy_0.1.0_amd64.deb" | awk '{print $1}')"
esha="$(sha256sum "$tmp/elsewhere/escape.deb" | awk '{print $1}')"

run() { # run <manifest> <log> [VAR=VAL ...]
  local man="$1" log="$2"; shift 2
  : > "$log"
  env NALA_RELEASES_SSV="$man" NALA_OS_RELEASE="$tmp/os-release" NALA_DEVUAN_VERSION_FILE="$tmp/no-devuan" \
    NALA_ARCH=amd64 NALA_HOSTNAME=t480s DOTCORTEX_HOSTS_SSV="$ROOT/all/.config/dotcortex/hosts.ssv" \
    NALA_LOCAL_DEB_ROOTS="$tmp/builds" NALA_TEST_STATE="$tmp/no-state" NALA_TEST_LOG="$log" \
    HOME="$tmp/home" XDG_CACHE_HOME="$tmp/cache" PATH="$stubbin:$PATH" "$@" "$HELPER"
}

row() { printf '%s\n' '# repo package asset_name_or_glob arch scope extra' "$1"; }

expect_refuse() { # expect_refuse <name> <manifest> <pattern> [VAR=VAL ...]
  local name="$1" man="$2" pat="$3"; shift 3
  local out rc=0
  out="$(run "$man" "$tmp/refuse.log" "$@" 2>&1)" || rc=$?
  [ "$rc" -ne 0 ] || { echo "$name: unexpectedly accepted" >&2; exit 1; }
  grep -q -- "$pat" <<<"$out" || { echo "$name: missing '$pat' in: $out" >&2; exit 1; }
  if [ -s "$tmp/refuse.log" ]; then echo "$name: refused row still called apt/curl: $(cat "$tmp/refuse.log")" >&2; exit 1; fi
}

good="file://$tmp/builds/Caddy_0.1.0_amd64.deb caddy Caddy_0.1.0_amd64.deb amd64 t480s 0.1.0,$sha"
row "$good" > "$tmp/good.ssv"

# Correct entry accepted in dry-run: prints the plan, installs nothing, writes no cache file.
out="$(run "$tmp/good.ssv" "$tmp/log" NALA_RELEASE_DIFF_ONLY=1 2>&1)"
grep -q 'release: pkg=caddy arch=amd64 latest=0.1.0 installed=' <<<"$out"
if [ -s "$tmp/log" ]; then echo "dry-run called apt/curl: $(cat "$tmp/log")" >&2; exit 1; fi
if find "$tmp/cache/nala/releases" -type f 2>/dev/null | grep -q .; then
  echo "dry-run wrote cache files" >&2; exit 1
fi

# Full run reuses the shared install path: sudo nala install --no-autoremove <pinned file>.
rpath="$(realpath -- "$tmp/builds/Caddy_0.1.0_amd64.deb")"
printf 'install ok installed\t0.0.9\n' > "$tmp/state"
out="$(run "$tmp/good.ssv" "$tmp/log" NALA_TEST_STATE="$tmp/state" NALA_TEST_REPAIR=1 2>&1)"
grep -q 'release: pkg=caddy arch=amd64 latest=0.1.0 installed=0.0.9' <<<"$out"
grep -q 'installing Caddy_0.1.0_amd64.deb with nala' <<<"$out"
grep -qF "nala:install -y --no-autoremove $rpath" "$tmp/log"
if grep -q curl-called "$tmp/log"; then echo "file:// row downloaded something" >&2; exit 1; fi
if [ -e "$tmp/cache/nala/releases/caddy" ]; then echo "file:// row wrote a cache copy" >&2; exit 1; fi

# Refusals: each must exit non-zero, say why, and never reach apt/curl.
row "file://$tmp/builds/Caddy_0.1.0_amd64.deb caddy Caddy_0.1.0_amd64.deb amd64 t480s 0.1.0,0000000000000000000000000000000000000000000000000000000000000000" > "$tmp/badsha.ssv"
expect_refuse wrong-sha "$tmp/badsha.ssv" 'SHA-256 mismatch'
row "$good" > "$tmp/badmeta.ssv"
expect_refuse wrong-pkg "$tmp/badmeta.ssv" "Package 'other' != manifest PKG 'caddy'" NALA_TEST_DEB_PKG=other
expect_refuse wrong-version "$tmp/badmeta.ssv" "Version '9.9.9' != EXTRA version '0.1.0'" NALA_TEST_DEB_VER=9.9.9
expect_refuse wrong-arch "$tmp/badmeta.ssv" "Architecture 'arm64' != manifest ARCH 'amd64'" NALA_TEST_DEB_ARCH=arm64
row "file://$tmp/elsewhere/escape.deb caddy escape.deb amd64 t480s 0.1.0,$esha" > "$tmp/outside.ssv"
expect_refuse outside-root "$tmp/outside.ssv" 'outside the allowed roots'
row "file://$tmp/builds/../elsewhere/escape.deb caddy escape.deb amd64 t480s 0.1.0,$esha" > "$tmp/dotdot.ssv"
expect_refuse dotdot-escape "$tmp/dotdot.ssv" 'outside the allowed roots'
row "file://$tmp/builds/link.deb caddy link.deb amd64 t480s 0.1.0,$sha" > "$tmp/symlink.ssv"
expect_refuse symlink "$tmp/symlink.ssv" 'not a symlink'
row "file://$tmp/builds/Caddy_0.1.0_amd64.deb caddy Caddy_0.1.0_amd64.deb amd64 t480s \"\"" > "$tmp/noextra.ssv"
expect_refuse missing-extra "$tmp/noextra.ssv" 'needs EXTRA version,sha256'
row "file://builds/Caddy_0.1.0_amd64.deb caddy Caddy_0.1.0_amd64.deb amd64 t480s 0.1.0,$sha" > "$tmp/rel.ssv"
expect_refuse non-absolute "$tmp/rel.ssv" 'must be absolute'

# Host scope: the t480s row applies on t480s only.
out="$(run "$tmp/good.ssv" "$tmp/log" NALA_RELEASE_DIFF_ONLY=1 NALA_HOSTNAME=x230 2>&1)"
grep -q 'skip caddy (scope=t480s, this=ubuntu)' <<<"$out"

# Default allowed root is $HOME/mnt/x230/HelmCortex/NEXUS/builds when NALA_LOCAL_DEB_ROOTS is unset.
mkdir -p "$tmp/home/mnt/x230/HelmCortex/NEXUS/builds"
cp "$tmp/builds/Caddy_0.1.0_amd64.deb" "$tmp/home/mnt/x230/HelmCortex/NEXUS/builds/"
dsha="$(sha256sum "$tmp/home/mnt/x230/HelmCortex/NEXUS/builds/Caddy_0.1.0_amd64.deb" | awk '{print $1}')"
row "file://$tmp/home/mnt/x230/HelmCortex/NEXUS/builds/Caddy_0.1.0_amd64.deb caddy Caddy_0.1.0_amd64.deb amd64 t480s 0.1.0,$dsha" > "$tmp/defaultroot.ssv"
out="$(run "$tmp/defaultroot.ssv" "$tmp/log" NALA_RELEASE_DIFF_ONLY=1 NALA_LOCAL_DEB_ROOTS= 2>&1)"
grep -q 'release: pkg=caddy arch=amd64 latest=0.1.0 installed=' <<<"$out"

# Non-file:// sources unchanged: direct:// still resolves from EXTRA, non-HTTPS still refused.
row 'direct://https://fixture.invalid/hugo.deb hugo hugo.deb amd64 shared 0.158.0,568fd95865802ad67b6af59793b78a538f0816b0cbe8d397e6a55311d3cda09c' > "$tmp/direct.ssv"
out="$(run "$tmp/direct.ssv" "$tmp/log" NALA_RELEASE_DIFF_ONLY=1 2>&1)"
grep -q 'release: pkg=hugo arch=amd64 latest=0.158.0 installed=' <<<"$out"
row 'direct://http://fixture.invalid/hugo.deb hugo hugo.deb amd64 shared 0.158.0,568fd95865802ad67b6af59793b78a538f0816b0cbe8d397e6a55311d3cda09c' > "$tmp/directhttp.ssv"
expect_refuse direct-non-https "$tmp/directhttp.ssv" 'refusing non-HTTPS asset URL'

printf '%s\n' 'nala release local file:// fixtures: ok'
