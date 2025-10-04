# ~/.dotfiles/all/.mk/appimage.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

APPS_DIR   := $(HOME)/Applications
BIN_DIR    := $(HOME)/.local/bin

INTEGRATE  := $(BIN_DIR)/appimage-integrator-setup
AIL_SCRUB  := $(BIN_DIR)/appimage-ail-scrub
HEALTH     := $(BIN_DIR)/appimage-health
UPDATE_ALL := $(BIN_DIR)/appimage-update-all
SCRUB_DESK := $(BIN_DIR)/appimage-scrub-desktops

.PHONY: appimage-integrate appimage-ail-scrub appimage-health \
        appimage-update appimage-update-all appimage-scrub-desktops

appimage-integrate: $(INTEGRATE)
| $(INTEGRATE)

appimage-ail-scrub: $(AIL_SCRUB)
| $(AIL_SCRUB)

appimage-health: $(HEALTH)
| $(HEALTH)

# New short verb
appimage-update: $(UPDATE_ALL)
| env SELF_UPDATE=1 $(UPDATE_ALL)

# Back-compat alias
appimage-update-all: appimage-update

# (kept for reference; no longer needed separately)
appimage-scrub-desktops: $(SCRUB_DESK)
| $(SCRUB_DESK)
