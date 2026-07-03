.RECIPEPREFIX := |
SHELL := /bin/bash

AM_MF        := $(HOME)/DotCortex/all/.am/manifest/apps.ssv
AM_BOOTSTRAP := $(HOME)/DotCortex/all/.local/bin/am-bootstrap
AM_CAPTURE   := $(HOME)/DotCortex/all/.local/bin/am-capture
AM_DIFF      := $(HOME)/DotCortex/all/.local/bin/am-diff
AM_APPLY     := $(HOME)/DotCortex/all/.local/bin/am-apply
AM_HEALTH    := $(HOME)/DotCortex/all/.local/bin/am-health

.PHONY: am-bootstrap am-capture am-diff am-apply am-apply-dry am-enforce am-update am-clean am-health

am-bootstrap:
| $(AM_BOOTSTRAP)

am-capture:
| $(AM_CAPTURE)

am-diff:
| $(AM_DIFF)

am-apply:
| $(AM_APPLY) --yes $(AM_MF)

am-apply-dry:
| $(AM_APPLY) --dry $(AM_MF)

am-enforce:
| $(AM_APPLY) --yes --remove-extra $(AM_MF)

am-update:
| PATH="$(HOME)/.local/bin:$$PATH" appman -u

am-clean:
| PATH="$(HOME)/.local/bin:$$PATH" appman -c

am-health:
| $(AM_HEALTH)
