# -*- mode: makefile-gmake; indent-tabs-mode: t; tab-width: 8 -*-
# Recipes use '|' instead of a literal TAB (GNU Make 3.82+).
.RECIPEPREFIX := |

EMACS ?= emacs
SCRIPT = all/.local/bin/dotfiles-batch.el
ROOT   = $(PWD)
GUIX ?= guix
GUIX_HOME := $(HOME)/.config/guix
EXTRA := $(HOME)/.guix-extra-profiles

# --- Stow packages you normally manage here ---
STOW_PKGS ?= all linux debian think

.PHONY: toc tangle all guix-pull guix-core guix-dev guix-gc guix-dirs \
        stow safe-stow x11-apply bridge-flatpak bridge-flatpak-reset

EMACS_BATCH = $(EMACS) --batch -Q \
  --eval "(setq create-lockfiles nil make-backup-files nil auto-save-default nil backup-inhibited t vc-make-backup-files nil)"

toc:
| $(EMACS_BATCH) --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-update "$(ROOT)")'

tangle:
| $(EMACS_BATCH) --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-tangle "$(ROOT)")'

guix-dirs:
| @chmod +x $(HOME)/.local/bin/guix-mkdirs 2>/dev/null || true
| @$(HOME)/.local/bin/guix-mkdirs

# keep profiles dirs around and keep manifests fresh
all: toc tangle guix-dirs

guix-pull:
| $(GUIX) pull

# make sure manifests are freshly tangled BEFORE we build the profile
guix-core: tangle guix-dirs
| mkdir -p $(EXTRA)/core
| $(GUIX) package -m $(GUIX_HOME)/manifests/core.scm -p $(EXTRA)/core/core

# dev depends on core being up-to-date
guix-dev: guix-core
| mkdir -p $(EXTRA)/dev
| $(GUIX) package -m $(GUIX_HOME)/manifests/dev.scm -p $(EXTRA)/dev/dev

guix-gc:
| $(GUIX) gc


# ---------- Stow helpers ----------
# Plain stow (no auto-backups). Use when you’re sure targets are symlinks or absent.
stow:
| cd $(HOME)/.dotfiles && stow $(STOW_PKGS)

# Safe stow: pre-backup any real files that would be replaced by stow.
# Looks for “existing target is neither a link nor a directory” and backs those up.
safe-stow:
| cd $(HOME)/.dotfiles && \
| for pkg in $(STOW_PKGS); do \
|   stow -n $$pkg 2>&1 \
|     | sed -n 's/.*\* existing target is neither a link nor a directory: \(.*\)$$/\1/p' \
|     | while read -r t; do \
|         if [ -f "$(HOME)/$$t" ] && [ ! -L "$(HOME)/$$t" ]; then \
|           cp -a "$(HOME)/$$t" "$(HOME)/$$t.bak.$$(date +%Y%m%d-%H%M%S)"; \
|         fi; \
|       done; \
|   stow $$pkg; \
| done


# ---------- X11 ----------
# Rebuild and stow X11 config (e.g. think/.xsessionrc). Uses normal stow to keep it managed.
x11-apply: tangle
| cd $(HOME)/.dotfiles && stow think
| @echo "✅ X11 applied (think/.xsessionrc now managed via stow)."


# ---------- Flatpak Bridge ----------
# Apply the repo-versioned bridge (fonts + cursors, dynamic). Idempotent.
bridge-flatpak: tangle stow
| if [ -x "$(HOME)/.local/bin/flatpak-desktop-bridge" ]; then \
|   "$(HOME)/.local/bin/flatpak-desktop-bridge"; \
| else \
|   echo "❌ Missing $(HOME)/.local/bin/flatpak-desktop-bridge. Tangle/stow your scripts first."; \
|   exit 1; \
| fi

bridge-flatpak-reset:
| if [ -x "$(HOME)/.local/bin/flatpak-desktop-bridge-reset" ]; then \
|   "$(HOME)/.local/bin/flatpak-desktop-bridge-reset"; \
| else \
|   echo "❌ Missing $(HOME)/.local/bin/flatpak-desktop-bridge-reset. Tangle/stow your scripts first."; \
|   exit 1; \
| fi
