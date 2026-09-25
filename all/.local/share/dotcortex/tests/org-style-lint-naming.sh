#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../../.." && pwd)"
LINT="$ROOT/all/.local/bin/org-style-lint"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/README.org" <<'EOF'
| Prefix         | Family                                   |
| =package-*=    | fixture                                  |
| =widgets-*=    | fixture family added in the same commit  |
EOF
for f in package-foo.org shell.org layers.org widgets.org widgets-bar.org newfamily-thing.org Bad_Name.org; do
  printf '* fixture\n' >"$tmp/$f"
done

out="$(cd "$tmp" && bash "$LINT" 2>&1 || true)"
expect() { printf '%s\n' "$out" | grep -qF -- "$1" || { echo "missing warning: $1" >&2; printf '%s\n' "$out" >&2; exit 1; }; }
refute() { if printf '%s\n' "$out" | grep -qF -- "$1"; then echo "unexpected warning: $1" >&2; exit 1; fi; }

expect "?? naming: newfamily-thing.org matches no documented namespace"
expect "?? naming: Bad_Name.org is not lowercase-kebab"
expect "?? naming: Bad_Name.org matches no documented namespace"
for ok in package-foo.org shell.org layers.org widgets.org widgets-bar.org README.org; do
  refute "naming: $ok"
done

# Warnings only: fatal just under STRICT_LINT=1, like the size budget.
(cd "$tmp" && bash "$LINT" >/dev/null 2>&1) || { echo "naming warnings must not be fatal" >&2; exit 1; }
if (cd "$tmp" && STRICT_LINT=1 bash "$LINT" >/dev/null 2>&1); then
  echo "STRICT_LINT=1 must make naming warnings fatal" >&2
  exit 1
fi

# The real repo root is clean.
real="$(cd "$ROOT" && bash "$LINT" 2>&1 || true)"
if printf '%s\n' "$real" | grep -q '^?? naming:'; then
  echo "repo root has naming warnings:" >&2
  printf '%s\n' "$real" | grep '^?? naming:' >&2
  exit 1
fi
echo "org-style-lint naming: ok"
