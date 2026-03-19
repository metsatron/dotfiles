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
#   cd ~/DotCortex && bash INSTALL.sh
#
# Idempotent — safe to re-run. Each phase checks whether its
# work has already been done and skips if so.
#
# IMPORTANT: This script must be run from an interactive terminal.
# The Guix installer requires stdin for confirmation prompts.
# Do NOT pipe this script (e.g. curl | bash) — it will fail at
# the Guix phase.
#
# Tested on:
#   - Devuan 6 (excalibur) / sysv-init / x86_64
#   - Debian 13 (trixie) / systemd / x86_64
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

# ── Detect init system ────────────────────────────────────────
INIT_SYSTEM="unknown"
if [ -d /run/systemd/system ]; then
  INIT_SYSTEM="systemd"
elif [ -f /sbin/init ] && /sbin/init --version 2>&1 | grep -qi sysv; then
  INIT_SYSTEM="sysv-init"
elif command -v openrc &>/dev/null; then
  INIT_SYSTEM="openrc"
else
  # Devuan uses sysv-init but init --version may not report it
  if [ -f /etc/devuan_version ]; then
    INIT_SYSTEM="sysv-init"
  fi
fi
info "Init system: $INIT_SYSTEM"

# ── Root check ────────────────────────────────────────────────
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
  info "Running as user — will use sudo for system packages"
fi

# ══════════════════════════════════════════════════════════════
# Phase 1: System dependencies via apt/nala
# ══════════════════════════════════════════════════════════════
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

  # Emacs (needed for org-mode tangle — emacs-nox is sufficient,
  # no GUI required since we only use batch mode)
  emacs-nox

  # Python
  python3
  python3-pip
  python3-venv

  # Node.js / npm: provided by Guix core profile (Phase 3.5) or nodesource.
  # NOT installed here — system npm conflicts with nodesource nodejs.

  # Shell utilities
  keychain       # SSH key agent
  zoxide         # smart cd replacement
  jq             # JSON processor
  tree           # directory viewer
  rsync          # file sync
  htop           # process monitor
  neofetch       # system info display

  # Build essentials for compiled packages
  build-essential
  libssl-dev
  libfreetype-dev
  libfontconfig-dev
  pkg-config
)

# LESSON: On Devuan (sysv-init), the Guix installer needs `daemonize`
# to background the daemon. Without it, the installer fails with
# "Missing commands: daemonize". Install it preemptively.
if [ "$INIT_SYSTEM" = "sysv-init" ]; then
  PKGS+=(daemonize)
fi

$SUDO $APT update -y
$SUDO $APT install -y "${PKGS[@]}"
ok "System packages installed"

# ══════════════════════════════════════════════════════════════
# Phase 2: Clone or locate DotCortex
# ══════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════
# Phase 3: GNU Guix
# ══════════════════════════════════════════════════════════════
# Guix provides the Guile Scheme interpreter that powers `loom`,
# plus hermetic package management for dev tools (nvim, etc).
#
# LESSONS LEARNED:
#
# 1. The official guix-install.sh REQUIRES interactive stdin.
#    It checks `read` and will fail with "Can't read standard
#    input. Hint: don't pipe scripts into a shell." if stdin
#    is not a terminal. You CANNOT use `yes | bash guix-install.sh`.
#
# 2. On Devuan/sysv-init, the installer needs the `daemonize`
#    package (installed in Phase 1 above).
#
# 3. The ftpmirror.gnu.org redirector sometimes sends you to
#    mirrors with broken SSL. If the official installer fails
#    to download, use the manual method below which fetches
#    from ftp.gnu.org directly.
#
# 4. After install, the daemon must be started manually on
#    sysv-init systems (no systemd unit auto-activation).
#
# We try the official installer first. If it fails (common on
# non-interactive runs), we fall back to manual installation.
# ══════════════════════════════════════════════════════════════
info "Phase 3: GNU Guix"

GUIX_VERSION="1.5.0"
GUIX_ARCH="x86_64-linux"

if command -v guix &>/dev/null; then
  ok "Guix already installed"
else
  info "Installing GNU Guix ${GUIX_VERSION}..."

  # Try official installer first (needs interactive terminal)
  GUIX_INSTALLED=false

  if [ -t 0 ]; then
    info "Attempting official installer (interactive)..."
    cd /tmp
    curl -sL https://git.savannah.gnu.org/cgit/guix.git/plain/etc/guix-install.sh -o guix-install.sh
    chmod +x guix-install.sh
    if $SUDO bash guix-install.sh; then
      GUIX_INSTALLED=true
      ok "Guix installed via official script"
    else
      warn "Official installer failed — falling back to manual install"
    fi
  else
    warn "Non-interactive terminal — using manual install method"
  fi

  # Manual fallback
  if [ "$GUIX_INSTALLED" = false ]; then
    info "Manual Guix installation..."

    GUIX_TARBALL="guix-binary-${GUIX_VERSION}.${GUIX_ARCH}.tar.xz"
    GUIX_URL="https://ftp.gnu.org/gnu/guix/${GUIX_TARBALL}"

    # Download
    cd /tmp
    if [ ! -f "$GUIX_TARBALL" ]; then
      info "Downloading ${GUIX_TARBALL} (~130MB)..."
      wget -q --show-progress "$GUIX_URL" -O "$GUIX_TARBALL"
    fi

    # Extract to /gnu/store and /var/guix
    info "Extracting to /gnu/store..."
    $SUDO mkdir -p /gnu/store
    $SUDO tar --warning=no-timestamp -xf "$GUIX_TARBALL"
    $SUDO mv var/guix /var/ 2>/dev/null || true
    $SUDO mv gnu/store/* /gnu/store/ 2>/dev/null || true

    # Create build users (guixbuilder01..10)
    info "Creating build users..."
    $SUDO groupadd --system guixbuild 2>/dev/null || true
    for i in $(seq -w 1 10); do
      $SUDO useradd -g guixbuild -G guixbuild \
        -d /var/empty -s /usr/sbin/nologin \
        -c "Guix build user $i" --system \
        "guixbuilder$i" 2>/dev/null || true
    done

    # Symlink daemon and CLI into /usr/local/bin
    $SUDO ln -sf /var/guix/profiles/per-user/root/current-guix/bin/guix-daemon \
      /usr/local/bin/guix-daemon
    $SUDO ln -sf /var/guix/profiles/per-user/root/current-guix/bin/guix \
      /usr/local/bin/guix

    # Set up root profile
    $SUDO mkdir -p ~root/.config/guix
    $SUDO ln -sf /var/guix/profiles/per-user/root/current-guix \
      ~root/.config/guix/current 2>/dev/null || true

    # Authorize the official CI substitute server
    # This lets Guix download pre-built binaries instead of compiling
    $SUDO /usr/local/bin/guix archive --authorize \
      < /var/guix/profiles/per-user/root/current-guix/share/guix/ci.guix.gnu.org.pub \
      2>/dev/null || true

    # Start the daemon
    if [ "$INIT_SYSTEM" = "sysv-init" ]; then
      # Create sysv init script
      $SUDO tee /etc/init.d/guix-daemon > /dev/null << 'INITSCRIPT'
#!/bin/sh
### BEGIN INIT INFO
# Provides:          guix-daemon
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: GNU Guix daemon
### END INIT INFO

DAEMON=/usr/local/bin/guix-daemon
DAEMON_ARGS="--build-users-group=guixbuild"
PIDFILE=/var/run/guix-daemon.pid

case "$1" in
  start)
    echo "Starting guix-daemon..."
    daemonize -p "$PIDFILE" "$DAEMON" $DAEMON_ARGS
    ;;
  stop)
    echo "Stopping guix-daemon..."
    [ -f "$PIDFILE" ] && kill $(cat "$PIDFILE") && rm -f "$PIDFILE"
    ;;
  restart)
    $0 stop; sleep 1; $0 start
    ;;
  status)
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
      echo "guix-daemon is running"
    else
      echo "guix-daemon is not running"
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
INITSCRIPT
      $SUDO chmod +x /etc/init.d/guix-daemon
      $SUDO update-rc.d guix-daemon defaults 2>/dev/null || true
      $SUDO daemonize /usr/local/bin/guix-daemon --build-users-group=guixbuild
      ok "Guix daemon started (sysv-init)"

    elif [ "$INIT_SYSTEM" = "systemd" ]; then
      # Systemd unit should already exist from the tarball
      $SUDO systemctl enable guix-daemon 2>/dev/null || true
      $SUDO systemctl start guix-daemon 2>/dev/null || true
      ok "Guix daemon started (systemd)"

    else
      warn "Unknown init system — start guix-daemon manually:"
      warn "  guix-daemon --build-users-group=guixbuild &"
    fi

    ok "Guix installed via manual method"
  fi

  # Set up user profile
  mkdir -p "$HOME/.config/guix"
  ln -sf /var/guix/profiles/per-user/"$(whoami)"/current-guix \
    "$HOME/.config/guix/current" 2>/dev/null || true

  # Make guix available in this session
  GUIX_PROFILE="$HOME/.config/guix/current"
  if [ -f "$GUIX_PROFILE/etc/profile" ]; then
    . "$GUIX_PROFILE/etc/profile"
  fi
  export PATH="/usr/local/bin:$PATH"
fi

# ══════════════════════════════════════════════════════════════
# Phase 3.5: Guix pull + core profile
# ══════════════════════════════════════════════════════════════
# LESSONS LEARNED:
#
# 1. guix pull must run BEFORE guix package — it updates the
#    channel/package list. First run takes ~15 minutes.
#
# 2. The core profile manifest lives at
#    ~/.config/guix/manifests/core.scm (placed by stow).
#    On first run, stow hasn't happened yet, so we use the
#    tangled output directly from DotCortex.
#
# 3. Guix substituter occasionally crashes with
#    "Wrong type argument in position 1: #f" during download
#    progress display. This is cosmetic — retry and cached
#    substitutes make the second attempt fast.
#
# 4. /tmp must have 1777 permissions or guix build sandboxes
#    fail with "bind: Permission denied". Phase 5 handles this.
# ══════════════════════════════════════════════════════════════
if command -v guix &>/dev/null; then
  info "Phase 3.5: Guix pull + core profile"

  # Ensure /tmp is writable for guix build sandboxes
  if ! touch /tmp/.guix-perm-test 2>/dev/null; then
    if [ -n "$SUDO" ]; then
      $SUDO chmod 1777 /tmp
      ok "/tmp permissions fixed for guix"
    fi
  else
    rm -f /tmp/.guix-perm-test
  fi

  info "Running guix pull (first run takes ~15 minutes)..."
  guix pull 2>&1 || warn "guix pull failed — retry manually: guix pull"

  # Re-source after pull
  GUIX_PROFILE="$HOME/.config/guix/current"
  if [ -f "$GUIX_PROFILE/etc/profile" ]; then
    . "$GUIX_PROFILE/etc/profile"
  fi

  # Apply core profile from tangled manifest (stow hasn't run yet)
  CORE_MANIFEST="$DOTCORTEX/all/.config/guix/manifests/core.scm"
  if [ -f "$CORE_MANIFEST" ]; then
    info "Installing Guix core profile (59+ packages — emacs, nvim, zsh, etc)..."
    mkdir -p "$HOME/.guix-extra-profiles/core"
    guix package -m "$CORE_MANIFEST" \
      -p "$HOME/.guix-extra-profiles/core/core" 2>&1 \
      || warn "Guix core profile had issues — retry: guix package -m $CORE_MANIFEST -p ~/.guix-extra-profiles/core/core"
    ok "Guix core profile installed"
  else
    warn "Core manifest not found at $CORE_MANIFEST — tangle first, then run: loom guix:apply"
  fi
else
  warn "Guix not available — skipping guix pull + core profile"
fi

# Add Guix core profile to PATH for remaining phases (npm, guile, etc)
GUIX_CORE="$HOME/.guix-extra-profiles/core/core"
if [ -d "$GUIX_CORE/bin" ]; then
  export PATH="$GUIX_CORE/bin:$PATH"
  info "Guix core profile on PATH: $GUIX_CORE/bin"
fi

# ══════════════════════════════════════════════════════════════
# Phase 4: Ensure directories
# ══════════════════════════════════════════════════════════════
info "Phase 4: Creating standard directories"

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.config"
mkdir -p "$HOME/.npm-global"
mkdir -p "$HOME/.guix-extra-profiles"

# Set npm prefix to avoid needing sudo for global installs
npm config set prefix "$HOME/.npm-global" 2>/dev/null || true

ok "Directories ready"

# ══════════════════════════════════════════════════════════════
# Phase 5: Tangle
# ══════════════════════════════════════════════════════════════
# LESSON: On first tangle, the Makefile tries to `include` all
# .mk fragment files (flatpak.mk, guix.mk, pip.mk, etc). If
# any don't exist yet (because they haven't been tangled), make
# will fail with "No rule to make target". Solution: create
# empty stubs for any missing .mk files before the first tangle.
# ══════════════════════════════════════════════════════════════
info "Phase 5: Tangling org files"

cd "$DOTCORTEX"

if command -v emacs &>/dev/null; then
  # Ensure .mk stubs exist so Makefile includes don't fail
  mkdir -p all/.mk
  for mk in flatpak guix guix-substitutes snap appimage cargo homebrew npm pip nala; do
    [ -f "all/.mk/${mk}.mk" ] || touch "all/.mk/${mk}.mk"
  done

  # Ensure manifest directories exist for tangle targets
  mkdir -p all/.pip/manifest
  mkdir -p all/.npm/manifest
  mkdir -p all/.snap/manifest
  mkdir -p all/.cargo/manifest
  mkdir -p all/.appimage/inventory
  mkdir -p all/.app/manifest
  mkdir -p all/.homebrew/manifest

  # LESSON: If /tmp has restrictive permissions (755 instead of 1777),
  # BOTH emacs org-persist AND guix build sandboxes break with
  # "Permission denied". Fix it at the root if we have sudo.
  if ! touch /tmp/.dotcortex-perm-test 2>/dev/null; then
    warn "/tmp is not writable (permissions may be 755 instead of 1777)"
    if [ -n "$SUDO" ]; then
      info "Fixing /tmp permissions..."
      $SUDO chmod 1777 /tmp
      ok "/tmp permissions fixed"
    else
      warn "Cannot fix /tmp — using ~/.cache/tmp as TMPDIR for tangle"
      export TMPDIR="$HOME/.cache/tmp"
      mkdir -p "$TMPDIR"
    fi
  else
    rm -f /tmp/.dotcortex-perm-test
  fi

  make tangle 2>&1 || warn "Tangle had warnings (check output above)"
  ok "Tangled"
else
  warn "Emacs not found — skipping tangle. Install emacs-nox and re-run."
fi

# ══════════════════════════════════════════════════════════════
# Phase 5.5: Pre-place loom + maak.scm (chicken-and-egg fix)
# ══════════════════════════════════════════════════════════════
# LESSON: loom needs ~/.config/maak/maak.scm (placed by stow)
# and Guix guile. You CANNOT use `loom stow:x230` for the first
# stow — but after this phase, loom will work for subsequent runs.
# ══════════════════════════════════════════════════════════════
info "Phase 5.5: Pre-placing loom and maak.scm"

if [ -f "$DOTCORTEX/all/.config/maak/maak.scm" ]; then
  mkdir -p "$HOME/.config/maak"
  cp "$DOTCORTEX/all/.config/maak/maak.scm" "$HOME/.config/maak/maak.scm"
  ok "Pre-placed maak.scm"
fi

if [ -f "$DOTCORTEX/all/.local/bin/loom" ]; then
  mkdir -p "$HOME/.local/bin"
  cp "$DOTCORTEX/all/.local/bin/loom" "$HOME/.local/bin/loom"
  chmod +x "$HOME/.local/bin/loom"
  ok "Pre-placed loom"
fi

# ══════════════════════════════════════════════════════════════
# Phase 6: Stow
# ══════════════════════════════════════════════════════════════
# LESSONS LEARNED:
#
# 1. safe-stow's sed pattern must handle THREE stow message formats:
#    - stow <2.4: "existing target is neither a link nor a directory: FILE"
#    - stow 2.4+: "cannot stow PKG/FILE over existing target FILE since neither..."
#    - repo rename: "existing target is not owned by stow: FILE"
#    The loom.org safe-stow target handles all three.
#
# 2. HelmCortex symlink conflict: On machines where ~/HelmCortex is a
#    user-managed symlink (e.g. T480s: ~/HelmCortex -> ~/mnt/x230/HelmCortex),
#    stow cannot merge into it and reports "existing target is not owned
#    by stow". Solution: the sed output is piped through
#    { grep -v '^HelmCortex$' || true; } to filter it out.
#    If stow still fails, we auto-retry with --ignore='HelmCortex'.
#
# 3. Absolute symlinks in overlay dirs (e.g. .config/guix/current ->
#    /var/guix/profiles/...) cause stow to abort. Remove them before
#    stowing — they're machine-specific and shouldn't be stow-managed.
#
# 4. Backup files (.bak.TIMESTAMP) in $HOME can confuse stow on
#    subsequent runs. Use --ignore='\.bak\.' to skip them.
# ══════════════════════════════════════════════════════════════
info "Phase 6: Stowing overlays"

cd "$DOTCORTEX"

# Remove absolute symlinks that stow can't handle
find all/ linux/ debian/ devuan/ x230/ t480s/ -type l 2>/dev/null | while read -r link; do
  target=$(readlink "$link" 2>/dev/null || true)
  if [ -n "$target" ] && [[ "$target" = /* ]]; then
    warn "Removing absolute symlink: $link -> $target"
    rm "$link"
  fi
done

# Detect which overlays to apply
OVERLAYS="all"

if [ -f /etc/debian_version ] || [ -f /etc/devuan_version ]; then
  OVERLAYS="$OVERLAYS linux debian"
fi

# Devuan / sysv-init overlay (non-systemd daemons, XFCE panel launchers)
if [ -f /etc/devuan_version ] || [ "$INIT_SYSTEM" = "sysv-init" ]; then
  OVERLAYS="$OVERLAYS devuan"
fi

# ThinkPad detection — X230 vs T480s
if [ -d /sys/devices/platform/thinkpad_acpi ] || \
   $SUDO dmidecode -s system-product-name 2>/dev/null | grep -qi thinkpad; then
  PRODUCT=$($SUDO dmidecode -s system-product-name 2>/dev/null || echo "unknown")
  case "$PRODUCT" in
    *X230*|*x230*)
      OVERLAYS="$OVERLAYS x230"
      info "Detected ThinkPad X230"
      ;;
    *T480s*|*t480s*|*T480*)
      OVERLAYS="$OVERLAYS t480s"
      info "Detected ThinkPad T480s"
      ;;
    *)
      # Generic ThinkPad — use x230 overlay as default
      OVERLAYS="$OVERLAYS x230"
      info "Detected ThinkPad: $PRODUCT (using x230 overlay)"
      ;;
  esac
fi

info "Stowing: $OVERLAYS"

# Detect if HelmCortex is a symlink (mounted machine)
STOW_IGNORE=""
if [ -L "$HOME/HelmCortex" ]; then
  info "HelmCortex is a symlink — ignoring it during stow"
  STOW_IGNORE="--ignore=HelmCortex"
fi

# Backup conflicting real files and stow each overlay
for pkg in $OVERLAYS; do
  info "Processing overlay: $pkg"

  # Detect files that need backup (handles all three stow message formats)
  { stow -n $pkg 2>&1 || true; } \
    | sed -n \
      -e 's/.*existing target is neither a link nor a directory: \(.*\)$/\1/p' \
      -e 's/.*over existing target \(.*\) since neither.*/\1/p' \
      -e 's/.*existing target is not owned by stow: \(.*\)$/\1/p' \
    | { grep -v '^HelmCortex$' || true; } \
    | while read -r t; do
        case "$t" in /*) abs="$t" ;; *) abs="$HOME/$t" ;; esac
        if [ -e "$abs" ] || [ -L "$abs" ]; then
          ts=$(date +%Y%m%d-%H%M%S)
          info "  backup $abs -> $abs.bak.$ts"
          cp -a "$abs" "$abs.bak.$ts" 2>/dev/null || true
          rm -rf "$abs"
        fi
      done

  # Stow with appropriate ignores
  if stow $STOW_IGNORE --ignore='\.bak\.' $pkg 2>&1; then
    ok "Stowed: $pkg"
  else
    warn "Stow $pkg had issues (check output above)"
  fi
done

ok "All overlays processed"

# ══════════════════════════════════════════════════════════════
# Phase 7: pip packages
# ══════════════════════════════════════════════════════════════
info "Phase 7: Installing pip packages from manifest"

if [ -x "$HOME/.local/bin/pip-apply" ]; then
  "$HOME/.local/bin/pip-apply" || true
elif [ -f "$DOTCORTEX/all/.local/bin/pip-apply" ]; then
  bash "$DOTCORTEX/all/.local/bin/pip-apply" || true
fi
ok "Pip packages applied"

# ══════════════════════════════════════════════════════════════
# Phase 8: npm packages
# ══════════════════════════════════════════════════════════════
info "Phase 8: Installing npm packages from manifest"

if [ -x "$HOME/.local/bin/npm-apply" ]; then
  ENFORCE=0 UNINSTALL=0 UPDATE=0 "$HOME/.local/bin/npm-apply" || true
elif [ -f "$DOTCORTEX/all/.local/bin/npm-apply" ]; then
  ENFORCE=0 UNINSTALL=0 UPDATE=0 bash "$DOTCORTEX/all/.local/bin/npm-apply" || true
fi
ok "Npm packages applied"

# ══════════════════════════════════════════════════════════════
# Phase 8.5: Cargo / Rust packages
# ══════════════════════════════════════════════════════════════
# LESSONS LEARNED:
#
# 1. cargo-apply uses dotcortex-rust-env which auto-installs rustup
#    if ~/.cargo/bin/cargo doesn't exist. No manual rust install needed.
#
# 2. Build scripts (proc-macro2, libc, etc) need a C compiler (gcc/cc).
#    build-essential MUST be installed first (Phase 1). Without it,
#    cargo install fails with "could not compile `libc` (build script)".
#
# 3. The cargo manifest uses awk to parse SSV. mawk (Debian/Devuan
#    default) does NOT support POSIX [[:space:]] character classes —
#    only gawk does. All awk patterns must use [ \t] instead.
#
# 4. The "host" lane in the manifest uses cargo-wrap, which expects
#    cargo already in PATH (designed for Guix cargo). On machines
#    where cargo comes from rustup (~/.cargo/bin/cargo), ensure
#    ~/.cargo/bin is in PATH before running cargo-apply, or use
#    dotcortex-rust-env directly.
# ══════════════════════════════════════════════════════════════
info "Phase 8.5: Cargo / Rust packages"

# Ensure cargo is available (dotcortex-rust-env bootstraps rustup if needed)
if [ -x "$HOME/.local/bin/dotcortex-rust-env" ]; then
  "$HOME/.local/bin/dotcortex-rust-env" cargo --version || true
  info "Cargo available — installing crates from manifest"
  export PATH="$HOME/.cargo/bin:$PATH"
  if [ -x "$HOME/.local/bin/cargo-apply" ]; then
    "$HOME/.local/bin/cargo-apply" || true
  elif [ -f "$DOTCORTEX/all/.local/bin/cargo-apply" ]; then
    bash "$DOTCORTEX/all/.local/bin/cargo-apply" || true
  fi
else
  warn "dotcortex-rust-env not found — skipping cargo packages. Tangle and stow first."
fi
ok "Cargo packages applied"

# ══════════════════════════════════════════════════════════════
# Phase 9: Claude Code
# ══════════════════════════════════════════════════════════════
info "Phase 9: Claude Code"

if command -v claude &>/dev/null; then
  ok "Claude Code already installed"
else
  info "Installing Claude Code via npm..."
  npm install -g @anthropic-ai/claude-code 2>/dev/null \
    || warn "Claude Code install failed — install manually: npm install -g @anthropic-ai/claude-code"
fi

# ══════════════════════════════════════════════════════════════
# Phase 10: PATH and shell integration
# ══════════════════════════════════════════════════════════════
info "Phase 10: PATH and shell integration"

BASHRC="$HOME/.bashrc"

# Ensure HelmCortex FORGE/bin is on PATH (for auryn, pipelines)
if ! grep -q 'HelmCortex/FORGE/bin' "$BASHRC" 2>/dev/null; then
  if [ -d "$HOME/HelmCortex/FORGE/bin" ]; then
    cat >> "$BASHRC" << 'FORGE_PATH'

# HelmCortex FORGE bin (auryn, pipelines, scripts)
if [ -d "$HOME/HelmCortex/FORGE/bin" ]; then
  export PATH="$HOME/HelmCortex/FORGE/bin:$PATH"
fi
FORGE_PATH
    ok "Added FORGE/bin to PATH in .bashrc"
  fi
fi

# Ensure Guix profile is sourced in bashrc
if ! grep -q 'guix/current' "$BASHRC" 2>/dev/null; then
  cat >> "$BASHRC" << 'GUIX_PROFILE'

# GNU Guix user profile
GUIX_PROFILE="$HOME/.config/guix/current"
if [ -f "$GUIX_PROFILE/etc/profile" ]; then
  . "$GUIX_PROFILE/etc/profile"
fi
GUIX_PROFILE
  ok "Added Guix profile sourcing to .bashrc"
fi

# ══════════════════════════════════════════════════════════════
# Done
# ══════════════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════════════════"
printf "${G}DotCortex bootstrap complete.${N}\n"
echo ""
echo "Next steps:"
echo "  1. Set zsh as default shell:"
echo "     GUIX_ZSH=\$HOME/.guix-extra-profiles/core/core/bin/zsh"
echo "     grep -qxF \"\$GUIX_ZSH\" /etc/shells || echo \"\$GUIX_ZSH\" | sudo tee -a /etc/shells"
echo "     chsh -s \"\$GUIX_ZSH\""
echo "  2. Log out and back in (or: source ~/.zshenv && exec zsh)"
echo "  3. loom                  (verify all loom verbs work)"
echo "  4. loom flatpak:apply    (install Flatpak apps from manifest)"
echo ""
echo "Verify everything:"
echo "  loom stow:health         (check for broken symlinks)"
echo "  loom cargo:health        (check rust/cargo status)"
echo "  loom pip:diff            (see pip drift from manifest)"
echo "  loom npm:diff            (see npm drift from manifest)"
echo ""
echo "Machine-specific stow verbs:"
echo "  loom stow:x230           (X230: all linux debian x230)"
echo "  loom stow:t480s          (T480s: all linux debian devuan t480s)"
echo "════════════════════════════════════════════════════"
