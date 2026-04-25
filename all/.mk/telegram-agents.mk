# Makefile Fragment


# [[file:../../telegram-agents.org::*Makefile Fragment][Makefile Fragment:1]]
# ~/DotCortex/all/.mk/telegram-agents.mk
.PHONY: telegram-agents-list telegram-agents-status telegram-agents-enable
.PHONY: telegram-agents-disable telegram-agents-start telegram-agents-stop
.PHONY: telegram-agents-sync telegram-agents-switch

telegram-agents-list:
	@chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
	$(HOME)/.local/bin/telegram-agent-host list

telegram-agents-status:
	@chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
	$(HOME)/.local/bin/telegram-agent-host status

telegram-agents-enable:
	@chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
	$(HOME)/.local/bin/telegram-agent-host enable $(AGENT)

telegram-agents-disable:
	@chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
	$(HOME)/.local/bin/telegram-agent-host disable $(AGENT)

telegram-agents-start:
	@chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
	$(HOME)/.local/bin/telegram-agent-host start

telegram-agents-stop:
	@chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
	$(HOME)/.local/bin/telegram-agent-host stop

telegram-agents-sync:
	@chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
	$(HOME)/.local/bin/telegram-agent-host sync

telegram-agents-switch:
	@chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
	$(HOME)/.local/bin/telegram-agent-host switch $(MACHINE)
# Makefile Fragment:1 ends here
