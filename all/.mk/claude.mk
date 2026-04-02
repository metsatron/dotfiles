# ~/DotCortex/all/.mk/claude.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: claude-apply claude-health

claude-apply:
| @chmod +x $(HOME)/.local/bin/claude-plugins-apply 2>/dev/null || true
| $(HOME)/.local/bin/claude-plugins-apply

claude-health:
| @chmod +x $(HOME)/.local/bin/claude-plugins-health 2>/dev/null || true
| $(HOME)/.local/bin/claude-plugins-health
