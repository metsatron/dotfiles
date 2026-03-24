# ~/DotCortex/all/.mk/bun.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: bun-capture bun-diff bun-sync bun-apply bun-health bun-source-diff bun-source-sync bun-source-apply bun-source-update bun-source-health

bun-capture:
| @chmod +x $(HOME)/.local/bin/bun-capture 2>/dev/null || true
| $(HOME)/.local/bin/bun-capture

bun-diff:
| @chmod +x $(HOME)/.local/bin/bun-diff 2>/dev/null || true
| $(HOME)/.local/bin/bun-diff

bun-sync:
| @chmod +x $(HOME)/.local/bin/bun-apply 2>/dev/null || true
| ENFORCE=0 UNINSTALL=0 UPDATE=0 $(HOME)/.local/bin/bun-apply

bun-apply:
| @chmod +x $(HOME)/.local/bin/bun-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=1 UPDATE=0 $(HOME)/.local/bin/bun-apply

bun-health:
| @chmod +x $(HOME)/.local/bin/bun-health 2>/dev/null || true
| $(HOME)/.local/bin/bun-health

bun-source-diff:
| @chmod +x $(HOME)/.local/bin/bun-source-diff 2>/dev/null || true
| $(HOME)/.local/bin/bun-source-diff

bun-source-sync:
| @chmod +x $(HOME)/.local/bin/bun-source-sync 2>/dev/null || true
| $(HOME)/.local/bin/bun-source-sync

bun-source-apply:
| @chmod +x $(HOME)/.local/bin/bun-source-apply 2>/dev/null || true
| $(HOME)/.local/bin/bun-source-apply

bun-source-update:
| @chmod +x $(HOME)/.local/bin/bun-source-update 2>/dev/null || true
| $(HOME)/.local/bin/bun-source-update

bun-source-health:
| @chmod +x $(HOME)/.local/bin/bun-source-health 2>/dev/null || true
| $(HOME)/.local/bin/bun-source-health
