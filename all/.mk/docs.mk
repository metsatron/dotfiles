# ~/DotCortex/all/.mk/docs.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: docs-build docs-clean

docs-build:
| @chmod +x $(HOME)/.local/bin/dotcortex-docs-build $(HOME)/.local/bin/dotcortex-docset-gen 2>/dev/null || true
| $(HOME)/.local/bin/dotcortex-docs-build

docs-clean:
| rm -rf $(HOME)/.local/share/dotcortex/docsets
