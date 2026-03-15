# ~/DotCortex/all/.mk/homebrew.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: brew-apply brew-health

brew-apply:
| @chmod +x $(HOME)/.local/bin/brew-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=1 UPDATE=1 $(HOME)/.local/bin/brew-apply

brew-health:
| @chmod +x $(HOME)/.local/bin/brew-health 2>/dev/null || true
| $(HOME)/.local/bin/brew-health
