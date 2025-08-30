#!/bin/bash
# === Create robust launchers for your three profiles ===
set -euo pipefail

BIN="$HOME/.local/bin"
CORE="$HOME/.emacs.d.spacemacs"           # where we parked Spacemacs core above
PROFILES_DIR="$HOME/.emacs.profiles"      # tiny sandbox homes (for legacy Emacs)
mkdir -p "$BIN" "$PROFILES_DIR"

make_spc() {
  local name="$1" spcdir="$2"
  local launcher="$BIN/spc-$name"

  cat > "$launcher" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
# --- Config injected by generator ---
NAME="__NAME__"
SPC_DIR="__SPCDIR__"
CORE="__CORE__"
PROFILES_DIR="__PROFILES_DIR__"

# Check Emacs major version (prefer 29+ for --init-directory)
EMV="$(emacs --batch --eval '(princ emacs-major-version)' 2>/dev/null || echo 27)"

if [ "$EMV" -ge 29 ] && emacs --help 2>&1 | grep -q -- '--init-directory'; then
  # Clean: run Spacemacs directly from its own dir; per-profile config via SPACEMACSDIR
  exec env SPACEMACSDIR="$SPC_DIR" emacs --init-directory "$CORE" "$@"
else
  # Legacy fallback: sandboxed HOME so ~/.emacs.d resolves to Spacemacs core,
  # and ~/.spacemacs.d resolves to the chosen profile — all *outside* real $HOME.
  HOME_TMP="$PROFILES_DIR/home-spacemacs-$NAME"
  mkdir -p "$HOME_TMP"
  ln -sfn "$CORE"    "$HOME_TMP/.emacs.d"
  ln -sfn "$SPC_DIR" "$HOME_TMP/.spacemacs.d"
  exec env HOME="$HOME_TMP" emacs "$@"
fi
EOF

  # Fill placeholders
  sed -i \
    -e "s#__NAME__#$name#g" \
    -e "s#__SPCDIR__#$(printf %q "$spcdir")#g" \
    -e "s#__CORE__#$(printf %q "$CORE")#g" \
    -e "s#__PROFILES_DIR__#$(printf %q "$PROFILES_DIR")#g" \
    "$launcher"

  chmod +x "$launcher"
  echo "Made launcher: $launcher"
}

make_spc "gpt"    "$HOME/.spacemacs.d.gpt"
make_spc "grok"   "$HOME/.spacemacs.d.grok"
make_spc "claude" "$HOME/.spacemacs.d.claude"

# Bonus helpers
printf '%s\n' \
'#!/usr/bin/env bash' 'exec emacs -Q "$@"' > "$BIN/emacs-vanilla"
chmod +x "$BIN/emacs-vanilla"

echo "Launchers ready. Try:  spc-gpt   spc-grok   spc-claude   (and emacs-vanilla)"

