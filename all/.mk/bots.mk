# Makefile Fragment


# [[file:../../bots.org::*Makefile Fragment][Makefile Fragment:1]]
# ~/DotCortex/all/.mk/bots.mk
.RECIPEPREFIX := |
.PHONY: bots-list bots-status bots-enable bots-disable bots-start bots-stop bots-sync bots-switch

bots-list:
| @chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
| $(HOME)/.local/bin/telegram-agent-host list

bots-status:
| @chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
| $(HOME)/.local/bin/telegram-agent-host status

bots-enable:
| @chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
| $(HOME)/.local/bin/telegram-agent-host enable $(AGENT)

bots-disable:
| @chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
| $(HOME)/.local/bin/telegram-agent-host disable $(AGENT)

bots-start:
| @chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
| $(HOME)/.local/bin/telegram-agent-host start

bots-stop:
| @chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
| $(HOME)/.local/bin/telegram-agent-host stop

bots-sync:
| @chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
| $(HOME)/.local/bin/telegram-agent-host sync

bots-switch:
| @chmod +x $(HOME)/.local/bin/telegram-agent-host 2>/dev/null || true
| $(HOME)/.local/bin/telegram-agent-host switch $(MACHINE)
# Makefile Fragment:1 ends here
