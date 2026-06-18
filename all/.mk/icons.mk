.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: icons-sync icon-inject

icons-sync:
| @HELPER="$(HOME)/.local/bin/icons-home-sync"; \
| if [ ! -x "$$HELPER" ]; then HELPER="$(HOME)/DotCortex/all/.local/bin/icons-home-sync"; fi; \
| chmod +x "$$HELPER" 2>/dev/null || true; \
| "$$HELPER"

icon-inject:
| @HELPER="$(HOME)/.local/bin/icon-theme-inject"; \
| if [ ! -x "$$HELPER" ]; then HELPER="$(HOME)/DotCortex/all/.local/bin/icon-theme-inject"; fi; \
| chmod +x "$$HELPER" 2>/dev/null || true; \
| "$$HELPER" $(ARGS)
