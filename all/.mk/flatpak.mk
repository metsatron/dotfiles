# Flatpak Make targets fragment. Safe to include or run standalone.
# Requires GNU Make 3.82+.

.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: flatpak-remotes flatpak-capture flatpak-diff flatpak-sync flatpak-apply

flatpak-remotes:
| @chmod +x $(HOME)/.local/bin/flatpak-remotes-setup 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-remotes-setup

flatpak-capture:
| @chmod +x $(HOME)/.local/bin/flatpak-capture 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-capture

flatpak-diff:
| @chmod +x $(HOME)/.local/bin/flatpak-diff 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-diff

# Additive only by default
flatpak-sync: flatpak-remotes
| @chmod +x $(HOME)/.local/bin/flatpak-apply 2>/dev/null || true
| ENFORCE=0 UNINSTALL=0 $(HOME)/.local/bin/flatpak-apply

# Enforce exact match. Set both flags to permit removals.
# Examples:
#   ENFORCE=1 UNINSTALL=1 make -f all/.mk/flatpak.mk flatpak-apply
#   FORCE_SUDO_SYSTEM=1 ENFORCE=1 UNINSTALL=1 make -f all/.mk/flatpak.mk flatpak-apply
flatpak-apply: flatpak-remotes
| @chmod +x $(HOME)/.local/bin/flatpak-apply 2>/dev/null || true
| ENFORCE=${ENFORCE} UNINSTALL=${UNINSTALL} FORCE_SUDO_SYSTEM=${FORCE_SUDO_SYSTEM} $(HOME)/.local/bin/flatpak-apply

# Flatpak bridge
bridge-flatpak: tangle stow
| if [ -x "$(HOME)/.local/bin/flatpak-desktop-bridge" ]; then \
|   "$(HOME)/.local/bin/flatpak-desktop-bridge"; \
| else \
|   echo "❌ Missing $(HOME)/.local/bin/flatpak-desktop-bridge. Tangle and stow first."; \
|   exit 1; \
| fi

bridge-flatpak-reset:
| if [ -x "$(HOME)/.local/bin/flatpak-desktop-bridge-reset" ]; then \
|   "$(HOME)/.local/bin/flatpak-desktop-bridge-reset"; \
| else \
|   echo "❌ Missing $(HOME)/.local/bin/flatpak-desktop-bridge-reset. Tangle and stow first."; \
|   exit 1; \
| fi
