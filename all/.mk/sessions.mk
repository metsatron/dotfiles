# ~/DotCortex/all/.mk/sessions.mk
.RECIPEPREFIX := |
.PHONY: sessions-once sessions-watch sessions-status

AGENT_SESSIOND ?= $(firstword $(wildcard $(HOME)/.local/bin/agent-sessiond $(HOME)/DotCortex/all/.local/bin/agent-sessiond))
AGENT_SESSION ?= $(firstword $(wildcard $(HOME)/.local/bin/agent-session $(HOME)/DotCortex/all/.local/bin/agent-session))

sessions-once:
| @chmod +x $(AGENT_SESSIOND) $(AGENT_SESSION) 2>/dev/null || true
| $(AGENT_SESSIOND) once

sessions-watch:
| @chmod +x $(AGENT_SESSIOND) $(AGENT_SESSION) 2>/dev/null || true
| $(AGENT_SESSIOND) watch

sessions-status:
| @chmod +x $(AGENT_SESSIOND) $(AGENT_SESSION) 2>/dev/null || true
| $(AGENT_SESSIOND) status
