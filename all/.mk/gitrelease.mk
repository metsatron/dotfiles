# GitHub release artifact targets. Flatpak bundles are owned by flatpak.org.
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: gitrelease-apply gitrelease-cache

gitrelease-apply:
| @chmod +x $(HOME)/.local/bin/gitrelease 2>/dev/null || true
| $(HOME)/.local/bin/gitrelease update-all

gitrelease-cache:
| @chmod +x $(HOME)/.local/bin/gitrelease 2>/dev/null || true
| $(HOME)/.local/bin/gitrelease list | while read -r app; do [ -n "$$app" ] && $(HOME)/.local/bin/gitrelease cache "$$app" || true; done
