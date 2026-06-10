.RECIPEPREFIX := |
SHELL := /bin/bash

PLASMOID_APPLY  := $(HOME)/DotCortex/linux/.local/bin/plasmoid-apply
PLASMOID_DIFF   := $(HOME)/DotCortex/linux/.local/bin/plasmoid-diff
PLASMOID_HEALTH := $(HOME)/DotCortex/linux/.local/bin/plasmoid-health
PLASMOID_RELOAD := $(HOME)/DotCortex/linux/.local/bin/plasmoid-reload
KWIN_BORDERLESS := $(HOME)/DotCortex/linux/.local/bin/kwin-borderless-maximized

.PHONY: plasmoid-apply plasmoid-diff plasmoid-health plasmoid-reload \
        kwin-borderless-status kwin-borderless-on kwin-borderless-off

plasmoid-apply:
| $(PLASMOID_APPLY)

plasmoid-diff:
| $(PLASMOID_DIFF)

plasmoid-health:
| $(PLASMOID_HEALTH)

plasmoid-reload:
| $(PLASMOID_RELOAD)

kwin-borderless-status:
| $(KWIN_BORDERLESS) status

kwin-borderless-on:
| $(KWIN_BORDERLESS) enable

kwin-borderless-off:
| $(KWIN_BORDERLESS) disable
