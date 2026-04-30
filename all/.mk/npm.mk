# ~/DotCortex/all/.mk/npm.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: npm-capture npm-diff npm-sync npm-update npm-apply npm-health

npm-capture:
| @chmod +x $(HOME)/.local/bin/npm-capture 2>/dev/null || true
| $(HOME)/.local/bin/npm-capture

npm-diff:
| @chmod +x $(HOME)/.local/bin/npm-diff 2>/dev/null || true
| $(HOME)/.local/bin/npm-diff

# Install anything new from the manifest, do not uninstall extras, do not touch existing versions.
npm-sync:
| @chmod +x $(HOME)/.local/bin/npm-apply 2>/dev/null || true
| ENFORCE=0 UNINSTALL=0 UPDATE=0 $(HOME)/.local/bin/npm-apply

# Install missing and update outdated packages, no removals.
npm-update:
| @chmod +x $(HOME)/.local/bin/npm-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=0 UPDATE=1 $(HOME)/.local/bin/npm-apply

# Strict apply, install and enforce manifest membership, but do not auto upgrade versions.
npm-apply:
| @chmod +x $(HOME)/.local/bin/npm-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=1 UPDATE=0 $(HOME)/.local/bin/npm-apply

npm-health:
| @chmod +x $(HOME)/.local/bin/npm-health 2>/dev/null || true
| $(HOME)/.local/bin/npm-health
