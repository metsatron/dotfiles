# ~/DotCortex/all/.mk/pip.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: pip-capture pip-diff pip-sync pip-apply pip-health

pip-capture:
| @chmod +x $(HOME)/.local/bin/pip-capture 2>/dev/null || true
| $(HOME)/.local/bin/pip-capture

pip-diff:
| @chmod +x $(HOME)/.local/bin/pip-diff 2>/dev/null || true
| $(HOME)/.local/bin/pip-diff

pip-sync:
| @chmod +x $(HOME)/.local/bin/pip-apply 2>/dev/null || true
| $(HOME)/.local/bin/pip-apply

pip-apply:
| @chmod +x $(HOME)/.local/bin/pip-apply 2>/dev/null || true
| $(HOME)/.local/bin/pip-apply

pip-health:
| @chmod +x $(HOME)/.local/bin/pip-health 2>/dev/null || true
| $(HOME)/.local/bin/pip-health
