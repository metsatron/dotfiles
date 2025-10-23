#!/usr/bin/env bash
set -o noclobber -o nounset -o pipefail

file="$1"
w="${2:-$COLUMNS}"
h="${3:-$LINES}"
x="${4:-0}"
y="${5:-0}"
tty="/dev/tty"

mime="$(file --mime-type -Lb "$file")"

case "$mime" in
  image/*)
    # 1) Kitty graphics with exact placement (works in WezTerm), write to the TTY
    if command -v kitty >/dev/null 2>&1 && [ -z "${TMUX:-}" ]; then
      printf '\e7' >"$tty"                                 # save cursor
      printf '\e[%d;%dH' "$((y+1))" "$((x+1))" >"$tty"     # move to preview pane origin
      kitty +kitten icat \
        --place "${w}x${h}@${x}x${y}" \
        --transfer-mode=memory \
        --stdin=no \
        "$file" >"$tty" 2>/dev/null || true
      printf '\e8' >"$tty"                                 # restore cursor
      exit 6
    fi

    # 2) WezTerm's imgcat (width in cells), write to the TTY
    if command -v wezterm-imgcat >/dev/null 2>&1; then
      printf '\e7' >"$tty"
      printf '\e[%d;%dH' "$((y+1))" "$((x+1))" >"$tty"
      WEZTERM_IMGCAT_WIDTH="${w}cell" wezterm-imgcat "$file" >"$tty" 2>/dev/null || true
      printf '\e8' >"$tty"
      exit 6
    fi

    # 3) High-quality text fallback (sixel), goes to stdout inside the pane
    if command -v chafa >/dev/null 2>&1; then
      chafa --format=sixel --size "${w}x${h}" "$file"
      exit 0
    fi

    # 4) Simple text fallback
    if command -v viu >/dev/null 2>&1; then
      viu -w "$w" "$file"
      exit 0
    fi

    echo "Image preview available but no graphics backend found."
    exit 0
    ;;
esac

exit 0
