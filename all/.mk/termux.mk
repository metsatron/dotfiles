# ~/DotCortex/all/.mk/termux.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: termux-pkg-apply termux-pkg-health

termux-pkg-apply:
| @chmod +x $(HOME)/.local/bin/termux-pkg-apply 2>/dev/null || true
| $(HOME)/.local/bin/termux-pkg-apply

termux-pkg-health:
| @chmod +x $(HOME)/.local/bin/termux-pkg-health 2>/dev/null || true
| $(HOME)/.local/bin/termux-pkg-health
