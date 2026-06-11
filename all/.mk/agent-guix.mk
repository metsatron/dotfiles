# all/.mk/agent-guix.mk
ifndef AGENT_GUIX_MK_INCLUDED
AGENT_GUIX_MK_INCLUDED := 1

.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: agent-guix-report agent-guix-apply agent-guix-verify \
        agent-provision-report agent-provision-apply agent-cli-report agent-cli-apply

agent-provision-report:
| @chmod +x $(HOME)/.local/bin/agent-provision 2>/dev/null || true
| $(HOME)/.local/bin/agent-provision

agent-provision-apply:
| @chmod +x $(HOME)/.local/bin/agent-provision 2>/dev/null || true
| $(HOME)/.local/bin/agent-provision --apply

agent-cli-report:
| @chmod +x $(HOME)/.local/bin/agent-cli-install 2>/dev/null || true
| $(HOME)/.local/bin/agent-cli-install

agent-cli-apply:
| @chmod +x $(HOME)/.local/bin/agent-cli-install 2>/dev/null || true
| $(HOME)/.local/bin/agent-cli-install --apply

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
