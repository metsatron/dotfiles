# Nala/apt Make targets fragment. Requires GNU Make 3.82+.
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: nala-repos nala-capture nala-diff nala-release-diff nala-release-sync nala-sync nala-apply nala-apply-auto nala-health

nala-repos:
| @chmod +x $(HOME)/.local/bin/nala-repos-setup 2>/dev/null || true
| $(HOME)/.local/bin/nala-repos-setup

nala-capture:
| @chmod +x $(HOME)/.local/bin/nala-capture 2>/dev/null || true
| $(HOME)/.local/bin/nala-capture

nala-diff:
| @chmod +x $(HOME)/.local/bin/nala-diff 2>/dev/null || true
| $(HOME)/.local/bin/nala-diff

nala-release-diff:
| @chmod +x $(HOME)/.local/bin/nala-release-diff 2>/dev/null || true
| $(HOME)/.local/bin/nala-release-diff

nala-release-sync:
| @chmod +x $(HOME)/.local/bin/nala-release-sync 2>/dev/null || true
| $(HOME)/.local/bin/nala-release-sync

nala-sync: nala-repos
| @chmod +x $(HOME)/.local/bin/nala-apply 2>/dev/null || true
| ENFORCE=0 UNINSTALL=0 $(HOME)/.local/bin/nala-apply

nala-apply: nala-repos
| sudo nala upgrade
| @chmod +x $(HOME)/.local/bin/nala-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=0 $(HOME)/.local/bin/nala-apply

# Same as nala-apply, but never asks. nala refuses to run without a terminal
# unless --assume-yes is passed, so an agent session (no TTY) cannot use
# nala-apply at all. Held-back packages stay held: this is `upgrade`, not
# `full-upgrade`, so kernel/ABI transitions still need a human.
nala-apply-auto: nala-repos
| sudo nala upgrade --assume-yes
| @chmod +x $(HOME)/.local/bin/nala-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=0 $(HOME)/.local/bin/nala-apply

nala-health:
| @chmod +x $(HOME)/.local/bin/nala-health 2>/dev/null || true
| $(HOME)/.local/bin/nala-health
