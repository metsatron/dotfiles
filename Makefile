# -*- mode: makefile-gmake; indent-tabs-mode: t; tab-width: 8 -*-
.RECIPEPREFIX := |

EMACS ?= emacs
SCRIPT = all/.local/bin/dotfiles-batch.el
ROOT   = $(PWD)
GUIX ?= guix
GUIX_HOME := $(HOME)/.config/guix
EXTRA := $(HOME)/.guix-extra-profiles

# Stow packages you normally manage here
STOW_PKGS ?= all

.PHONY: toc tangle all guix-pull guix-core guix-dev guix-gc guix-dirs \
        stow safe-stow x11-apply bridge-flatpak bridge-flatpak-reset preview-stow lint

lint:
| all/.local/bin/org-style-lint

# Make tangle depend on lint
tangle: lint

EMACS_BATCH = $(EMACS) --batch -Q \
  --eval "(setq create-lockfiles nil make-backup-files nil auto-save-default nil backup-inhibited t vc-make-backup-files nil)"

toc:
| $(EMACS_BATCH) --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-update "$(ROOT)")'

tangle:
| $(EMACS_BATCH) --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-tangle "$(ROOT)")'

# all = toc → tangle → guix-dirs only
all: toc tangle guix-dirs

# Plain stow
stow:
| cd $(HOME)/.dotfiles && stow $(STOW_PKGS)

# Safe stow with timestamped backups of real files
safe-stow:
| set -euo pipefail; \
| cd $(HOME)/.dotfiles; \
| for pkg in $(STOW_PKGS); do \
|   echo ">> preview $$pkg"; \
|   stow -n $$pkg 2>&1 \
|     | sed -n 's/.*\* existing target is neither a link nor a directory: \(.*\)$$/\1/p' \
|     | while read -r t; do \
|         case "$$t" in /*) abs="$$t" ;; *) abs="$(HOME)/$$t" ;; esac; \
|         if [ -e "$$abs" ] && [ ! -L "$$abs" ]; then \
|           ts=$$(date +%Y%m%d-%H%M%S); \
|           echo "   backup $$abs -> $$abs.bak.$$ts"; \
|           cp -a "$$abs" "$$abs.bak.$$ts"; \
|           echo "   remove  $$abs"; \
|           rm -rf "$$abs"; \
|         fi; \
|       done; \
|   echo ">> stow $$pkg"; \
|   stow $$pkg; \
| done

preview-stow:
| cd $(HOME)/.dotfiles && stow -n $(STOW_PKGS) || true

# X11 apply for think overlay
x11-apply: tangle
| cd $(HOME)/.dotfiles && stow think
| @echo "✅ X11 applied."

include $(HOME)/.dotfiles/all/.mk/flatpak.mk
include $(HOME)/.dotfiles/all/.mk/guix.mk
include $(HOME)/.dotfiles/all/.mk/guix-substitutes.mk
include $(HOME)/.dotfiles/all/.mk/snap.mk
include $(HOME)/.dotfiles/all/.mk/appimage.mk
include $(HOME)/.dotfiles/all/.mk/cargo.mk
include $(HOME)/.dotfiles/all/.mk/homebrew.mk
include $(HOME)/.dotfiles/all/.mk/npm.mk
