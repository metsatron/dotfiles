# ~/DotCortex/all/.mk/npm.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: npm-capture npm-diff npm-sync npm-apply npm-health

npm-capture:
| @chmod +x $(HOME)/.local/bin/npm-capture 2>/dev/null || true
| $(HOME)/.local/bin/npm-capture

npm-diff:
| @chmod +x $(HOME)/.local/bin/npm-diff 2>/dev/null || true
| $(HOME)/.local/bin/npm-diff

# Install missing packages and update tracked packages, but do not uninstall extras.
npm-sync:
| @chmod +x $(HOME)/.local/bin/npm-apply 2>/dev/null || true
| ENFORCE=0 UNINSTALL=0 UPDATE=1 $(HOME)/.local/bin/npm-apply

# Strict apply, install/update tracked packages, and enforce manifest membership.
npm-apply:
| @chmod +x $(HOME)/.local/bin/npm-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=1 UPDATE=1 $(HOME)/.local/bin/npm-apply

npm-health:
| @chmod +x $(HOME)/.local/bin/npm-health 2>/dev/null || true
| $(HOME)/.local/bin/npm-health
