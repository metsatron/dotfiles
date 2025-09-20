# 🛠️ Make Targets

# [[file:README.org::*🛠️ Make Targets][🛠️ Make Targets:1]]
EMACS ?= emacs
SCRIPT = all/.local/bin/dotfiles-batch.el
ROOT   = $(PWD)
GUIX ?= guix
GUIX_HOME := $(HOME)/.config/guix
EXTRA := $(HOME)/.guix-extra-profiles
.PHONY: toc tangle all guix-pull guix-core guix-dev guix-gc

EMACS_BATCH = $(EMACS) --batch -Q \
  --eval "(setq create-lockfiles nil make-backup-files nil auto-save-default nil backup-inhibited t vc-make-backup-files nil)"

toc:
    $(EMACS_BATCH) --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-update "$(ROOT)")'

tangle:
    $(EMACS_BATCH) --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-tangle "$(ROOT)")'

all: toc tangle

guix-pull:
    $(GUIX) pull

guix-core:
    mkdir -p $(EXTRA)/core
    $(GUIX) package -m $(GUIX_HOME)/manifests/core.scm -p $(EXTRA)/core/core

guix-dev:
    mkdir -p $(EXTRA)/dev
    $(GUIX) package -m $(GUIX_HOME)/manifests/dev.scm -p $(EXTRA)/dev/dev

guix-gc:
    $(GUIX) gc
# 🛠️ Make Targets:1 ends here
