# all/.mk/agent-guix.mk
ifndef AGENT_GUIX_MK_INCLUDED
AGENT_GUIX_MK_INCLUDED := 1

.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: agent-guix-report agent-guix-apply agent-guix-verify

agent-guix-report:
| @chmod +x $(HOME)/.local/bin/agent-guix-apply 2>/dev/null || true
| $(HOME)/.local/bin/agent-guix-apply

agent-guix-apply:
| @chmod +x $(HOME)/.local/bin/agent-guix-apply 2>/dev/null || true
| $(HOME)/.local/bin/agent-guix-apply --apply

agent-guix-verify:
| @set -e; for m in $(HOME)/DotCortex/all/.config/guix/manifests/agents/*.scm; do \
|   [ -e "$$m" ] || continue; \
|   t=$$(basename $$m .scm); u=agent-$$t; \
|   id $$u >/dev/null 2>&1 || { echo "$$u: no user"; continue; } ; \
|   echo "== $$u =="; \
|   sudo -u $$u -H sh -lc 'command -v node && node --version && npm --version' \
|     || echo "$$u: profile not ready"; \
| done

endif
