# Guix Make targets fragment

# [[file:../../guix.org::*Guix Make targets fragment][Guix Make targets fragment:1]]
# Guix Make targets fragment
.RECIPEPREFIX := |
SHELL := /bin/bash

GUIX ?= guix
GUIX_HOME := $(HOME)/.config/guix
EXTRA := $(HOME)/.guix-extra-profiles

.PHONY: guix-dirs guix-pull guix-core guix-dev guix-gc

guix-dirs:
| @chmod +x $(HOME)/.local/bin/guix-mkdirs 2>/dev/null || true
| @$(HOME)/.local/bin/guix-mkdirs

guix-pull:
| $(GUIX) pull

guix-core: guix-dirs
| mkdir -p $(EXTRA)/core
| $(GUIX) package -m $(GUIX_HOME)/manifests/core.scm -p $(EXTRA)/core/core

guix-dev: guix-core
| mkdir -p $(EXTRA)/dev
| $(GUIX) package -m $(GUIX_HOME)/manifests/dev.scm -p $(EXTRA)/dev/dev

guix-gc:
| $(GUIX) gc
# Guix Make targets fragment:1 ends here
