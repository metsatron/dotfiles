#!/usr/bin/env bash
set -euo pipefail
set -o noclobber

FILE_PATH="${1:-}"
PV_WIDTH="${2:-${COLUMNS:-80}}"
PV_HEIGHT="${3:-${LINES:-24}}"
IMAGE_CACHE_PATH="${4:-}"
PV_IMAGE_ENABLED="${5:-False}"

FILE_EXTENSION="${FILE_PATH##*.}"
FILE_EXTENSION_LOWER="$(printf '%s' "${FILE_EXTENSION:-}" | tr '[:upper:]' '[:lower:]')"
MIMETYPE="$(file --dereference --brief --mime-type -- "${FILE_PATH}")"

preview_text() {
  if command -v /home/metsatron/.cargo/bin/bat >/dev/null 2>&1; then
    # --theme=base16: bat's "base16" theme maps syntax roles onto the 16 base
    # ANSI color slots (0-15) rather than hardcoding hex, and those exact 16
    # slots are already wired to the LainCore/DreamWeave base16 palette in
    # kitty.conf/WezTerm (color0-15, see style.org emit-kitty). That makes the
    # preview pane inherit LainCore automatically and stay correct if the
    # palette is ever retuned in style.org, with no duplicated hex here.
    # base16-256 was rejected: its non-syntax roles fall back to the fixed
    # xterm 256-cube, which our terminal configs do not remap, so it would
    # drift from the theme. Plain "ansi" was rejected too: it drops down to
    # bare SGR with far fewer distinguished syntax roles than base16 offers
    # while inheriting the same terminal palette.
    /home/metsatron/.cargo/bin/bat \
      --color=always \
      --style=plain \
      --paging=never \
      --theme=base16 \
      --terminal-width="${PV_WIDTH:-80}" \
      -- "${FILE_PATH}" && exit 5
  fi

  if command -v pygmentize >/dev/null 2>&1; then
    pygmentize -f terminal256 -- "${FILE_PATH}" && exit 5
  fi

  cat -- "${FILE_PATH}" && exit 5
  exit 1
}

preview_pdf() {
  if command -v pdftotext >/dev/null 2>&1; then
    pdftotext -l 10 -nopgbrk -q -- "${FILE_PATH}" - | awk 'NR <= 1000 { print }' && exit 0
  fi
  exit 1
}

preview_image() {
  if [[ "${PV_IMAGE_ENABLED:-False}" == "True" ]]; then
    exit 7
  fi

  if command -v chafa >/dev/null 2>&1; then
    chafa --size "${PV_WIDTH:-80}x${PV_HEIGHT:-24}" -- "${FILE_PATH}" && exit 0
  fi

  file --brief -- "${FILE_PATH}"
  exit 0
}

preview_media_info() {
  file --brief -- "${FILE_PATH}" || true
python3 -c 'import os, sys, time
path = sys.argv[1]
st = os.stat(path)
print(f"Size: {st.st_size} bytes")
print("Modified: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)))' "${FILE_PATH}" || true
  exit 0
}

preview_archive() {
  if command -v bsdtar >/dev/null 2>&1; then
    bsdtar --list --file "${FILE_PATH}" && exit 0
  fi

  case "${FILE_EXTENSION_LOWER:-}" in
    zip)
      python3 -m zipfile -l "${FILE_PATH}" && exit 0
      ;;
    tar)
      python3 -m tarfile -l "${FILE_PATH}" && exit 0
      ;;
    tgz|gz|tbz|tbz2|txz|xz)
      python3 -m tarfile -l "${FILE_PATH}" && exit 0
      ;;
  esac

  file --brief -- "${FILE_PATH}"
  exit 0
}

case "${FILE_EXTENSION_LOWER:-}" in
  bash|bat|c|cc|cfg|conf|cpp|css|el|go|h|hpp|html|ini|java|js|json|lua|md|org|pl|py|rb|rs|scm|sh|toml|ts|xml|yaml|yml|zsh)
    preview_text
    ;;
  pdf)
    preview_pdf
    ;;
  zip|tar|tgz|gz|tbz|tbz2|txz|xz)
    preview_archive
    ;;
esac

case "${MIMETYPE:-}" in
  text/*|*/xml|application/json)
    preview_text
    ;;
  application/pdf)
    preview_pdf
    ;;
  image/*)
    preview_image
    ;;
  video/*|audio/*)
    preview_media_info
    ;;
  application/zip|application/x-tar|application/gzip|application/x-gzip|application/x-bzip2|application/x-xz)
    preview_archive
    ;;
esac

printf 'MIME: %s\n' "${MIMETYPE:-unknown}"
file --dereference --brief --mime -- "${FILE_PATH}"
exit 0
