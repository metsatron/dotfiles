.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: icons-sync icon-inject icon-cache-rebuild

icons-sync:
| @HELPER="$(HOME)/.local/bin/icons-home-sync"; \
| if [ ! -x "$$HELPER" ]; then HELPER="$(HOME)/DotCortex/all/.local/bin/icons-home-sync"; fi; \
| chmod +x "$$HELPER" 2>/dev/null || true; \
| "$$HELPER"

icon-cache-rebuild:
| @HELPER="$(HOME)/.local/bin/icon-cache-rebuild"; \
| if [ ! -x "$$HELPER" ]; then HELPER="$(HOME)/DotCortex/all/.local/bin/icon-cache-rebuild"; fi; \
| chmod +x "$$HELPER" 2>/dev/null || true; \
| "$$HELPER" $(ARGS)

icon-inject:
| @HELPER="$(HOME)/.local/bin/icon-theme-inject"; \
| if [ ! -x "$$HELPER" ]; then HELPER="$(HOME)/DotCortex/all/.local/bin/icon-theme-inject"; fi; \
| chmod +x "$$HELPER" 2>/dev/null || true; \
| "$$HELPER" $(ARGS)
