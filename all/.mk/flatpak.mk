# Flatpak Make targets fragment. Requires GNU Make 3.82+.
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: flatpak-remotes flatpak-capture flatpak-diff flatpak-release-diff flatpak-release-sync flatpak-sync flatpak-apply flatpak-perms-capture flatpak-perms-apply flatpak-bridge flatpak-bridge-reset

flatpak-remotes:
| @chmod +x $(HOME)/.local/bin/flatpak-remotes-setup 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-remotes-setup

flatpak-capture:
| @chmod +x $(HOME)/.local/bin/flatpak-capture 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-capture

flatpak-diff:
| @chmod +x $(HOME)/.local/bin/flatpak-diff 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-diff

flatpak-release-diff:
| @chmod +x $(HOME)/.local/bin/flatpak-release-diff 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-release-diff

flatpak-release-sync:
| @chmod +x $(HOME)/.local/bin/flatpak-release-sync 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-release-sync

# Additive only: installs + updates, no removals
flatpak-sync: flatpak-remotes
| @chmod +x $(HOME)/.local/bin/flatpak-apply 2>/dev/null || true
| ENFORCE=-1 UNINSTALL=-1 $(HOME)/.local/bin/flatpak-apply

# Default apply: enforce installs+updates; removals must be explicit (UNINSTALL=1)
flatpak-apply: flatpak-remotes
| @chmod +x $(HOME)/.local/bin/flatpak-apply 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-apply

flatpak-perms-capture:
| @chmod +x $(HOME)/.local/bin/flatpak-perms-capture 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-perms-capture

flatpak-perms-apply:
| @chmod +x $(HOME)/.local/bin/flatpak-perms-apply 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-perms-apply

flatpak-bridge:
| @chmod +x $(HOME)/.local/bin/flatpak-desktop-bridge 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-desktop-bridge

flatpak-bridge-reset:
| @chmod +x $(HOME)/.local/bin/flatpak-desktop-bridge-reset 2>/dev/null || true
| $(HOME)/.local/bin/flatpak-desktop-bridge-reset
