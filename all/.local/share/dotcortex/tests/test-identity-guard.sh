#!/usr/bin/env bash


# The test assembles its protected strings at runtime, so the fixture never contains a pattern the guard is looking for.


# [[file:../../../../../agents-hooks.org::*Protected-identity guard — the name a public repository must never carry][Protected-identity guard — the name a public repository must never carry:2]]
# ~/DotCortex/all/.local/share/dotcortex/tests/test-identity-guard.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
guard="${DOTCORTEX_IDENTITY_GUARD:-$here/../../../bin/dotcortex-identity-guard}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }

# The protected strings, assembled rather than written.
first="Fixture"; last="Protect${first}ed"; full="$first $last"
mail="$first.$last@example.invalid"
export DOTCORTEX_IDENTITY_DENYLIST="$tmp/denylist"
printf '%s\n%s\n# a comment\n' "$full" "$mail" > "$DOTCORTEX_IDENTITY_DENYLIST"

git init -q -b master "$tmp/r"; cd "$tmp/r"
git config user.email t@example.invalid; git config user.name t
echo base > a.txt; git add a.txt; git commit -qm base

# Content carrying the name is refused.
printf 'owner: %s\n' "$full" > b.txt; git add b.txt
"$guard" --staged 2>/dev/null && fail "staged content carrying the name was admitted"
# Content carrying the address is refused.
printf 'contact %s\n' "$mail" > b.txt; git add b.txt
"$guard" --staged 2>/dev/null && fail "staged content carrying the address was admitted"
# Committing AS that identity is refused, which a content scan alone would miss.
git reset -q; rm -f b.txt
echo clean > c.txt; git add c.txt
git -c user.name="$full" -c user.email="$mail" -c commit.gpgsign=false \
  -c core.hooksPath=/dev/null commit -qm ident 2>/dev/null || true
GIT_AUTHOR_NAME="$full" GIT_AUTHOR_EMAIL="$mail" "$guard" --staged 2>/dev/null \
  && fail "an author identity carrying the name was admitted"
# A clean staged change passes.
git reset -q --hard HEAD
echo "clean change" > c.txt; git add c.txt
"$guard" --staged || fail "a clean change was refused"
git commit -qm clean

# Pre-push refuses a range whose content carries the name, and passes otherwise.
old="$(git rev-parse HEAD)"
printf 'note %s\n' "$full" > d.txt; git add d.txt; git commit -qm leak
new="$(git rev-parse HEAD)"
printf 'refs/heads/master %s refs/heads/master %s\n' "$new" "$old" \
  | "$guard" --pre-push origin x 2>/dev/null && fail "pre-push admitted a leaking range"
git reset -q --hard "$old"
echo fine > e.txt; git add e.txt; git commit -qm fine
printf 'refs/heads/master %s refs/heads/master %s\n' "$(git rev-parse HEAD)" "$old" \
  | "$guard" --pre-push origin x || fail "pre-push refused a clean range"

# No denylist means nothing to protect: the guard allows everything and never wedges a fresh clone.
DOTCORTEX_IDENTITY_DENYLIST="$tmp/absent" "$guard" --staged || fail "guard refused without a denylist"
printf 'refs/heads/master %s refs/heads/master %s\n' "$(git rev-parse HEAD)" "$old" > "$tmp/refs"
DOTCORTEX_IDENTITY_DENYLIST="$tmp/absent" "$guard" --pre-push origin x < "$tmp/refs" \
  || fail "pre-push refused without a denylist"

echo "identity guard: all checks passed"
# Protected-identity guard — the name a public repository must never carry:2 ends here
