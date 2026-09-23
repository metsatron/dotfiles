# Nala/apt Make targets fragment. Requires GNU Make 3.82+.
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: nala-repos nala-capture nala-diff nala-release-diff nala-release-sync nala-sync nala-apply nala-apply-auto nala-health

# Gated hosts (package-host-gates.org): repo setup and upgrades never run from
# make; nala-apply itself plans a dry run (PROVISION_APPLY=1: additive installs).
PROVISION_GATE ?= $(firstword $(wildcard $(HOME)/.local/bin/provision-gate $(HOME)/DotCortex/all/.local/bin/provision-gate))
GATED = [ -n "$(PROVISION_GATE)" ] && "$(PROVISION_GATE)" is-gated
NALA_APPLY_BIN ?= $(firstword $(wildcard $(HOME)/.local/bin/nala-apply $(HOME)/DotCortex/debian/.local/bin/nala-apply) $(HOME)/.local/bin/nala-apply)

nala-repos:
| @if $(GATED); then echo "nala-repos: skipped on gated host (third-party repo setup is a reviewed, by-hand step there)"; exit 0; fi; \
|   chmod +x $(HOME)/.local/bin/nala-repos-setup 2>/dev/null || true; \
|   $(HOME)/.local/bin/nala-repos-setup

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
| @if $(GATED); then echo "nala upgrade: skipped on gated host (upgrades may remove packages)"; else sudo nala upgrade; fi
| @chmod +x $(NALA_APPLY_BIN) 2>/dev/null || true
| ENFORCE=1 UNINSTALL=0 $(NALA_APPLY_BIN)

# Same as nala-apply, but never asks. nala refuses to run without a terminal
# unless --assume-yes is passed, so an agent session (no TTY) cannot use
# nala-apply at all. Held-back packages stay held: this is `upgrade`, not
# `full-upgrade`, so kernel/ABI transitions still need a human.
nala-apply-auto: nala-repos
| @if $(GATED); then echo "nala upgrade: skipped on gated host (upgrades may remove packages)"; else sudo nala upgrade --assume-yes; fi
| @chmod +x $(NALA_APPLY_BIN) 2>/dev/null || true
| ENFORCE=1 UNINSTALL=0 $(NALA_APPLY_BIN)

nala-health:
| @chmod +x $(HOME)/.local/bin/nala-health 2>/dev/null || true
| $(HOME)/.local/bin/nala-health
