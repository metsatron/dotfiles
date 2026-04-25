# ~/DotCortex/all/.mk/bun.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: bun-capture bun-diff bun-sync bun-apply bun-health

bun-capture:
| @chmod +x $(HOME)/.local/bin/bun-capture 2>/dev/null || true
| $(HOME)/.local/bin/bun-capture

bun-diff:
| @chmod +x $(HOME)/.local/bin/bun-diff 2>/dev/null || true
| $(HOME)/.local/bin/bun-diff

bun-sync:
| @chmod +x $(HOME)/.local/bin/bun-apply 2>/dev/null || true
| ENFORCE=0 UNINSTALL=0 UPDATE=1 $(HOME)/.local/bin/bun-apply

bun-apply:
| @chmod +x $(HOME)/.local/bin/bun-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=1 UPDATE=1 $(HOME)/.local/bin/bun-apply

bun-health:
| @chmod +x $(HOME)/.local/bin/bun-health 2>/dev/null || true
| $(HOME)/.local/bin/bun-health
