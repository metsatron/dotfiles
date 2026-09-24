#!/usr/bin/env bash


# The test builds throwaway repositories and assembles every address at runtime, so this file never carries a literal the guard would refuse.


# [[file:../../../../../agents-hooks.org::*Network-address guard (rule 21)][Network-address guard (rule 21):2]]
# ~/DotCortex/all/.local/share/dotcortex/tests/test-address-guard.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
guard="${DOTCORTEX_ADDRESS_GUARD:-$here/../../../bin/dotcortex-address-guard}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
ip() { printf '%s.%s.%s.%s' "$@"; }
fail() { echo "FAIL: $*" >&2; exit 1; }

git init -q -b master "$tmp/r"; cd "$tmp/r"
git config user.email t@example.invalid; git config user.name t
echo base > a.txt; git add a.txt; git commit -qm base

# A tailnet address in a staged line is refused.
echo "host=$(ip 100 101 7 9)" > b.txt; git add b.txt
"$guard" --staged 2>/dev/null && fail "tailnet address was admitted"
# So is an RFC 1918 LAN address.
echo "lan=$(ip 192 168 1 20)" > b.txt; git add b.txt
"$guard" --staged 2>/dev/null && fail "LAN address was admitted"
# Version strings and public documentation ranges pass.
printf 'version 1.10.2.3\ndoc %s\n' "$(ip 192 0 2 1)" > b.txt; git add b.txt
"$guard" --staged || fail "a non-private dotted number was refused"
# The fixture allowlist admits exactly the named fake address.
echo "fixture=$(ip 100 64 0 1)" > b.txt; git add b.txt
"$guard" --staged || fail "the allowlisted fixture address was refused"
# Existing history never blocks: only added lines count.
git commit -qm fixture
echo "unrelated" > c.txt; git add c.txt
"$guard" --staged || fail "a clean commit was blocked by history"
git commit -qm clean

# Pre-push refuses a range that would publish an address, and passes otherwise.
git init -q --bare "$tmp/remote.git"; git remote add origin "$tmp/remote.git"
git push -q origin master
echo "host=$(ip 100 101 7 9)" > d.txt; git add d.txt; git commit -qm leak
new="$(git rev-parse HEAD)"; old="$(git rev-parse origin/master)"
printf 'refs/heads/master %s refs/heads/master %s\n' "$new" "$old" | "$guard" --pre-push origin x 2>/dev/null && fail "pre-push admitted a leaking range"
git reset -q --hard HEAD~1
echo ok > e.txt; git add e.txt; git commit -qm fine
printf 'refs/heads/master %s refs/heads/master %s\n' "$(git rev-parse HEAD)" "$old" | "$guard" --pre-push origin x || fail "pre-push refused a clean range"
echo "address guard: all checks passed"
# Network-address guard (rule 21):2 ends here
