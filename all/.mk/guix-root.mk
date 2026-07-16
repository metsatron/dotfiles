# all/.mk/guix-root.mk
ifndef GUIX_ROOT_MK_INCLUDED
GUIX_ROOT_MK_INCLUDED := 1

.RECIPEPREFIX := |
SHELL := /bin/bash
.ONESHELL:

GUIX ?= guix
ROOT_HOME := $(shell getent passwd root | cut -d: -f6)
ROOT_GUIX_HOME := $(ROOT_HOME)/.config/guix
ROOT_BENCH_DIR := $(ROOT_GUIX_HOME)/.bench
ROOT_PULL_CACHE := $(ROOT_BENCH_DIR)/pull-url

# Sync user channels and manifest to root
.PHONY: guix-root-sync
guix-root-sync:
| $(HOME)/DotCortex/all/.local/bin/root-sync

# Pull using the channels already synced into root
.PHONY: guix-root-pull
guix-root-pull: guix-root-sync
| sudo install -d -m 0755 $(ROOT_BENCH_DIR)
| sudo -i env GUIX_LOCPATH="$(ROOT_HOME)/.guix-profile/lib/locale" $(GUIX) pull \
|   -C "$(ROOT_GUIX_HOME)/channels.scm"

# Apply the root manifest
.PHONY: guix-root-apply
guix-root-apply: guix-root-pull
| sudo -i env GUIX_LOCPATH="$(ROOT_HOME)/.guix-profile/lib/locale" $(GUIX) package \
|   -m "$(ROOT_GUIX_HOME)/manifests/root.scm"

# Garbage collect at root scope
.PHONY: guix-root-gc
guix-root-gc:
| sudo -i $(GUIX) gc
endif
