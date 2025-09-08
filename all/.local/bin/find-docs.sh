#!/usr/bin/env bash
MODE="${1:-authored}"
ROOTS=( "$HOME/.dotfiles" "$HOME/HelmCortex" )

if [ "$MODE" = "all" ]; then
  PRUNE=( )
else
  PRUNE=( \( \
    -path '*/.git/*' -o \
    -path '*/.cache/*' -o \
    -path '*/node_modules/*' -o \
    -path "$HOME/.local/share/*" -o \
    -path "$HOME/.atom/packages/*" -o \
    -path "$HOME/.zplug/repos/*" -o \
    -path "$HOME/.config/emacs/.local/straight/repos/*" -o \
    -path "$HOME/.emacs.d.spacemacs/elpa/*" -o \
    -path "$HOME/HelmCortex/NEXUS/*" \
  \) -prune -o )
fi

echo "== README.org / README.md =="
for root in "${ROOTS[@]}"; do
  find "$root" "${PRUNE[@]}" -type f \( -iname 'README.org' -o -iname 'README.md' -o -iname 'readme.org' -o -iname 'readme.md' \) -print 2>/dev/null || true
done

echo
echo "== docs/ dirs with .org/.md =="
for root in "${ROOTS[@]}"; do
  mapfile -d '' docsdirs < <(find "$root" "${PRUNE[@]}" -type d -iname 'docs' -print0 2>/dev/null || true)
  for d in "${docsdirs[@]}"; do
    [ -d "$d" ] || continue
    find "$d" -type f \( -iname '*.org' -o -iname '*.md' \) -print 2>/dev/null || true
  done
done
