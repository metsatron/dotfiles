# ~/.dotfiles/all/.mk/app.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: app-apply app-health

app-apply:
| @chmod +x $(HOME)/.local/bin/app-apply 2>/dev/null || true
| $(HOME)/.local/bin/app-apply

app-health:
| @chmod +x $(HOME)/.local/bin/app-health 2>/dev/null || true
| $(HOME)/.local/bin/app-health
