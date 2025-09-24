# -*- mode: makefile-gmake; indent-tabs-mode: t; tab-width: 8 -*-
.RECIPEPREFIX := |

EMACS ?= emacs
SCRIPT = all/.local/bin/dotfiles-batch.el
ROOT   = $(PWD)
GUIX ?= guix
GUIX_HOME := $(HOME)/.config/guix
EXTRA := $(HOME)/.guix-extra-profiles

# Stow packages you normally manage here
STOW_PKGS ?= all linux debian think

.PHONY: toc tangle all guix-pull guix-core guix-dev guix-gc guix-dirs \
        stow safe-stow x11-apply bridge-flatpak bridge-flatpak-reset preview-stow

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

preview-stow:
| cd $(HOME)/.dotfiles && stow -n $(STOW_PKGS) || true

# X11 apply for think overlay
x11-apply: tangle
| cd $(HOME)/.dotfiles && stow think
| @echo "✅ X11 applied."
