# ~/DotCortex/all/.mk/appimage.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

APPS_DIR := $(HOME)/Applications
BIN_DIR := $(HOME)/.local/bin

INTEGRATE  := $(BIN_DIR)/appimage-integrator-setup
AIL_SCRUB  := $(BIN_DIR)/appimage-ail-scrub
HEALTH     := $(BIN_DIR)/appimage-health
UPDATE_ALL := $(BIN_DIR)/appimage-update-all
SCRUB_DESK := $(BIN_DIR)/appimage-scrub-desktops
INVENTORY  := $(BIN_DIR)/appimage-inventory
APRELEASE  := $(BIN_DIR)/apprelease

.PHONY: appimage-integrate appimage-ail-scrub appimage-health \
        appimage-update appimage-update-all appimage-scrub-desktops \
        appimage-inventory appimage-aprelease-list appimage-aprelease-update \
        appimage-aprelease-update-all

appimage-integrate: $(INTEGRATE)
| $(INTEGRATE)

appimage-ail-scrub: $(AIL_SCRUB)
| $(AIL_SCRUB)

appimage-health: $(HEALTH)
| $(HEALTH)

appimage-update: $(UPDATE_ALL)
| env SELF_UPDATE=1 $(UPDATE_ALL)

appimage-update-all: appimage-update

appimage-scrub-desktops: $(SCRUB_DESK)
| $(SCRUB_DESK)

appimage-inventory: $(INVENTORY)
| $(INVENTORY)

# apprelease verbs
appimage-aprelease-list: $(APRELEASE)
| $(APRELEASE) list

appimage-aprelease-update: $(APRELEASE)
| $(APRELEASE) update$(if $(filter 1,$(words $(filter-out $@,$(MAKECMDGOALS)))), $(word 2,$(filter-out $@,$(MAKECMDGOALS)))),)

appimage-aprelease-update-all: $(APRELEASE)
| $(APRELEASE) update-all
