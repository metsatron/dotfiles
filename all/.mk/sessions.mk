# ~/DotCortex/all/.mk/sessions.mk
.RECIPEPREFIX := |
.PHONY: sessions-once sessions-watch sessions-status sessions-top sessions-top-all sessions-cron

AGENT_SESSIOND ?= $(firstword $(wildcard $(HOME)/.local/bin/agent-sessiond $(HOME)/DotCortex/all/.local/bin/agent-sessiond))
AGENT_SESSION ?= $(firstword $(wildcard $(HOME)/.local/bin/agent-session $(HOME)/DotCortex/all/.local/bin/agent-session))
AGENT_TOP ?= $(firstword $(wildcard $(HOME)/.local/bin/agent-top $(HOME)/DotCortex/all/.local/bin/agent-top))
AGENT_SESSIOND_CRON ?= $(firstword $(wildcard $(HOME)/.local/bin/agent-sessiond-cron-apply $(HOME)/DotCortex/all/.local/bin/agent-sessiond-cron-apply))

sessions-once:
| @chmod +x $(AGENT_SESSIOND) $(AGENT_SESSION) 2>/dev/null || true
| $(AGENT_SESSIOND) once

sessions-watch:
| @chmod +x $(AGENT_SESSIOND) $(AGENT_SESSION) 2>/dev/null || true
| $(AGENT_SESSIOND) watch

sessions-status:
| @chmod +x $(AGENT_SESSIOND) $(AGENT_SESSION) 2>/dev/null || true
| $(AGENT_SESSIOND) status

sessions-top:
| @chmod +x $(AGENT_TOP) 2>/dev/null || true
| $(AGENT_TOP) once

sessions-top-all:
| @chmod +x $(AGENT_TOP) 2>/dev/null || true
| $(AGENT_TOP) once --all

sessions-cron:
| @chmod +x $(AGENT_SESSIOND_CRON) 2>/dev/null || true
| $(AGENT_SESSIOND_CRON)
