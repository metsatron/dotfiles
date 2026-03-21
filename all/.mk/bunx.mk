# ~/DotCortex/all/.mk/bunx.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: bunx-capture bunx-diff bunx-sync bunx-apply bunx-health

bunx-capture:
| @chmod +x $(HOME)/.local/bin/bunx-capture 2>/dev/null || true
| $(HOME)/.local/bin/bunx-capture

bunx-diff:
| @chmod +x $(HOME)/.local/bin/bunx-diff 2>/dev/null || true
| $(HOME)/.local/bin/bunx-diff

bunx-sync:
| @chmod +x $(HOME)/.local/bin/bunx-apply 2>/dev/null || true
| ENFORCE=0 UNINSTALL=0 $(HOME)/.local/bin/bunx-apply

bunx-apply:
| @chmod +x $(HOME)/.local/bin/bunx-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=1 $(HOME)/.local/bin/bunx-apply

bunx-health:
| @chmod +x $(HOME)/.local/bin/bunx-health 2>/dev/null || true
| $(HOME)/.local/bin/bunx-health
