# ~/DotCortex/all/.mk/claude.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: claude-plugins-apply claude-plugins-health

claude-plugins-apply:
| @chmod +x $(HOME)/.local/bin/claude-plugins-apply 2>/dev/null || true
| $(HOME)/.local/bin/claude-plugins-apply

claude-plugins-health:
| @chmod +x $(HOME)/.local/bin/claude-plugins-health 2>/dev/null || true
| $(HOME)/.local/bin/claude-plugins-health
