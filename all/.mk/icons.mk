.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: icons-sync

icons-sync:
| @HELPER="$(HOME)/.local/bin/icons-home-sync"; \
| if [ ! -x "$$HELPER" ]; then HELPER="$(HOME)/DotCortex/all/.local/bin/icons-home-sync"; fi; \
| chmod +x "$$HELPER" 2>/dev/null || true; \
| "$$HELPER"
