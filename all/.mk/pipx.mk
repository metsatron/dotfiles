# ~/DotCortex/all/.mk/pipx.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: pipx-apply pipx-health

pipx-apply:
| @chmod +x $(HOME)/.local/bin/pipx-apply 2>/dev/null || true
| $(HOME)/.local/bin/pipx-apply

pipx-health:
| @chmod +x $(HOME)/.local/bin/pipx-health 2>/dev/null || true
| $(HOME)/.local/bin/pipx-health
