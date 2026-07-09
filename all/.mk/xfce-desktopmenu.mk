.RECIPEPREFIX := |
SHELL := /bin/bash

XFCE_MENU_BUILD     := $(HOME)/DotCortex/linux/.local/bin/xfce-desktop-menubar-build
XFCE_MENU_CONFIGURE := $(HOME)/DotCortex/linux/.local/bin/xfce-desktopmenu-configure
XFWM_TITLELESS      := $(HOME)/DotCortex/linux/.local/bin/xfwm-titleless-maximized

.PHONY: xfce-menu xfce-menu-build xfce-menu-configure \
        xfwm-titleless-status xfwm-titleless-on xfwm-titleless-off

xfce-menu-build:
| $(XFCE_MENU_BUILD)

xfce-menu-configure:
| $(XFCE_MENU_CONFIGURE)

xfce-menu: xfce-menu-build xfce-menu-configure

xfwm-titleless-status:
| $(XFWM_TITLELESS) status

xfwm-titleless-on:
| $(XFWM_TITLELESS) enable

xfwm-titleless-off:
| $(XFWM_TITLELESS) disable
