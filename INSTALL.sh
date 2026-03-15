#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# DotCortex Bootstrap — Mètsàtron's Star Fleet Provisioner
# ═══════════════════════════════════════════════════════════════
# Gets a fresh Debian/Devuan machine to the point where `loom`
# and `make tangle && make safe-stow` work. After this script
# finishes, the operator can refine via nala.org, guix manifests,
# and loom verbs.
#
# Usage:
#   curl -sL <url>/INSTALL.sh | bash        # or
#   cd ~/DotCortex && bash INSTALL.sh
#
# Idempotent — safe to re-run.
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' C='\033[0;36m' N='\033[0m'
info()  { printf "${C}[info]${N}  %s\n" "$*"; }
ok()    { printf "${G}[ok]${N}    %s\n" "$*"; }
warn()  { printf "${Y}[warn]${N}  %s\n" "$*"; }
fail()  { printf "${R}[fail]${N}  %s\n" "$*" >&2; exit 1; }

# ── Detect OS ─────────────────────────────────────────────────
if [ -f /etc/os-release ]; then
  . /etc/os-release
else
  fail "Cannot detect OS — /etc/os-release missing"
fi
info "Detected: $PRETTY_NAME"

# ── Root check ────────────────────────────────────────────────
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
  info "Running as user — will use sudo for system packages"
fi

# ── Phase 1: System dependencies via apt/nala ─────────────────
info "Phase 1: Installing system dependencies"

# Prefer nala if available, fall back to apt
APT="apt-get"
if command -v nala &>/dev/null; then
  APT="nala"
  info "Using nala"
fi

PKGS=(
  # Core tools
  git
  stow
  curl
  wget
  make
  gcc

  # Emacs (needed for tangle)
  emacs-nox

  # Python
  python3
  python3-pip
  python3-venv

  # Node.js (for npm globals)
  nodejs
  npm

  # Shell utilities
  keychain
  zoxide
  jq
  tree
  rsync
  htop
  neofetch

  # Build essentials for compiled packages
  build-essential
  libssl-dev
  pkg-config
)

$SUDO $APT update -y
$SUDO $APT install -y "${PKGS[@]}"
ok "System packages installed"

# ── Phase 2: Clone or locate DotCortex ────────────────────────
info "Phase 2: Ensuring DotCortex is in place"

DOTCORTEX="$HOME/DotCortex"

if [ -d "$DOTCORTEX/.git" ]; then
  ok "DotCortex already cloned at $DOTCORTEX"
elif [ -d "$DOTCORTEX" ]; then
  warn "DotCortex directory exists but is not a git repo"
else
  info "Cloning DotCortex..."
  git clone --recursive https://gitlab.com/metsarono/dotfiles.git "$DOTCORTEX"
  cd "$DOTCORTEX" && git submodule update --recursive --remote
  ok "DotCortex cloned"
fi

cd "$DOTCORTEX"

# ── Phase 3: GNU Guix (user install) ─────────────────────────
info "Phase 3: GNU Guix"

if command -v guix &>/dev/null; then
  ok "Guix already installed"
else
  info "Installing GNU Guix (user daemon)..."
  # Official Guix install script
  cd /tmp
  curl -sL https://git.savannah.gnu.org/cgit/guix.git/plain/etc/guix-install.sh -o guix-install.sh
  chmod +x guix-install.sh
  $SUDO bash guix-install.sh
  ok "Guix installed — you may need to log out and back in"
fi

# ── Phase 4: Ensure directories ──────────────────────────────
info "Phase 4: Creating standard directories"

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.config"
mkdir -p "$HOME/.npm-global"
mkdir -p "$HOME/.guix-extra-profiles"

# Set npm prefix if not already set
npm config set prefix "$HOME/.npm-global" 2>/dev/null || true

ok "Directories ready"

# ── Phase 5: Tangle ──────────────────────────────────────────
info "Phase 5: Tangling org files"

cd "$DOTCORTEX"

if command -v emacs &>/dev/null; then
  make tangle 2>&1 || warn "Tangle had warnings (check output above)"
  ok "Tangled"
else
  warn "Emacs not found — skipping tangle. Install emacs-nox and re-run."
fi

# ── Phase 6: Stow ────────────────────────────────────────────
info "Phase 6: Stowing overlays"

cd "$DOTCORTEX"

# Detect which overlays to apply
OVERLAYS="all"

if [ -f /etc/debian_version ] || [ -f /etc/devuan_version ]; then
  OVERLAYS="$OVERLAYS linux debian"
fi

# ThinkPad detection
if [ -d /sys/devices/platform/thinkpad_acpi ] || \
   dmidecode -s system-product-name 2>/dev/null | grep -qi thinkpad; then
  OVERLAYS="$OVERLAYS think"
fi

info "Stowing: $OVERLAYS"
STOW_PKGS="$OVERLAYS" make safe-stow 2>&1 || warn "Stow had conflicts (check output above)"
ok "Stowed"

# ── Phase 7: pip packages ────────────────────────────────────
info "Phase 7: Installing pip packages from manifest"

if [ -x "$HOME/.local/bin/pip-apply" ]; then
  "$HOME/.local/bin/pip-apply"
elif [ -f "$DOTCORTEX/all/.local/bin/pip-apply" ]; then
  bash "$DOTCORTEX/all/.local/bin/pip-apply"
fi
ok "Pip packages applied"

# ── Phase 8: npm packages ────────────────────────────────────
info "Phase 8: Installing npm packages from manifest"

if [ -x "$HOME/.local/bin/npm-apply" ]; then
  ENFORCE=0 UNINSTALL=0 UPDATE=0 "$HOME/.local/bin/npm-apply" || true
elif [ -f "$DOTCORTEX/all/.local/bin/npm-apply" ]; then
  ENFORCE=0 UNINSTALL=0 UPDATE=0 bash "$DOTCORTEX/all/.local/bin/npm-apply" || true
fi
ok "Npm packages applied"

# ── Phase 9: Claude Code ─────────────────────────────────────
info "Phase 9: Claude Code"

if command -v claude &>/dev/null; then
  ok "Claude Code already installed"
else
  info "Installing Claude Code via npm..."
  npm install -g @anthropic-ai/claude-code 2>/dev/null || warn "Claude Code install failed — install manually"
fi

# ── Phase 10: PATH sanity ────────────────────────────────────
info "Phase 10: PATH verification"

# Check that key paths are in bashrc
BASHRC="$HOME/.bashrc"
NEED_FORGE=true

if grep -q 'HelmCortex/FORGE/bin' "$BASHRC" 2>/dev/null; then
  NEED_FORGE=false
fi

if [ "$NEED_FORGE" = true ] && [ -d "$HOME/HelmCortex/FORGE/bin" ]; then
  cat >> "$BASHRC" << 'FORGE_PATH'

# HelmCortex FORGE bin (auryn, pipelines, scripts)
if [ -d "$HOME/HelmCortex/FORGE/bin" ]; then
  export PATH="$HOME/HelmCortex/FORGE/bin:$PATH"
fi
FORGE_PATH
  ok "Added FORGE/bin to PATH in .bashrc"
fi

# ── Done ──────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════"
printf "${G}DotCortex bootstrap complete.${N}\n"
echo ""
echo "Next steps:"
echo "  1. Log out and back in (or source ~/.bashrc)"
echo "  2. Run 'guix pull' if Guix was just installed"
echo "  3. Run 'loom' to see all available verbs"
echo "  4. Fine-tune packages via nala.org, guix.org"
echo "════════════════════════════════════════════════════"
