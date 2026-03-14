.RECIPEPREFIX := |
SHELL := /bin/bash

SNAP_MF       := $(HOME)/.dotfiles/all/.snap/manifest/apps.ssv
SNAP_CAPTURE  := $(HOME)/.dotfiles/all/.local/bin/snap-capture
SNAP_DIFF     := $(HOME)/.dotfiles/all/.local/bin/snap-diff
SNAP_APPLY    := $(HOME)/.dotfiles/all/.local/bin/snap-apply-manifest
SNAP_AUTO     := $(HOME)/.dotfiles/all/.local/bin/snap-autoremove
SNAP_PRUNE    := $(HOME)/.dotfiles/all/.local/bin/snap-prune-disabled

.PHONY: snap-capture snap-diff snap-apply snap-apply-dry snap-enforce snap-enforce-force \
        snap-autoremove snap-autoremove-yes snap-autoremove-purge snap-prune-disabled \
        snap-list-orphans snap-connections

snap-capture:
| $(SNAP_CAPTURE)

snap-diff:
| $(SNAP_DIFF)

snap-apply:
| $(SNAP_APPLY) --yes $(SNAP_MF)

snap-apply-dry:
| $(SNAP_APPLY) --dry $(SNAP_MF)

snap-enforce:
| $(SNAP_APPLY) --yes --remove-extra $(SNAP_MF)

snap-enforce-force:
| $(SNAP_APPLY) --yes --remove-extra --force-protected $(SNAP_MF)

snap-autoremove:
| $(SNAP_AUTO)

snap-autoremove-yes:
| $(SNAP_AUTO) --yes

snap-autoremove-purge:
| $(SNAP_AUTO) --yes --purge-data

snap-prune-disabled:
| $(SNAP_PRUNE)

snap-list-orphans:
| comm -13 <(snap list | awk 'NR>1{print $$1}' | sort -u) <(ls -1 $(HOME)/snap 2>/dev/null | sort) \
|   | sed 's|^|orphan: $(HOME)/snap/|'

snap-connections:
| for s in gtk-common-themes gtk2-common-themes gnome-3-28-1804 gnome-42-2204; do \
|   echo "== $$s =="; snap connections $$s || true; echo; \
| done
