# all/.mk/guix.mk
ifndef GUIX_MK_INCLUDED
GUIX_MK_INCLUDED := 1

.RECIPEPREFIX := |
SHELL := /bin/bash
.SHELLFLAGS := -Eeuo pipefail -c
.ONESHELL:

GUIX ?= guix
GUIX_HOME := $(HOME)/.config/guix
EXTRA := $(HOME)/.guix-extra-profiles
LOCAL_PKGS := $(HOME)/.config/guix/local-packages
BENCH_DIR := $(GUIX_HOME)/.bench
PULL_CACHE := $(BENCH_DIR)/pull-url
FALLBACK_PULL_URLS ?= https://git.cbaines.net/guix/guix https://codeberg.org/guix/guix.git https://git.savannah.gnu.org/git/guix.git

.PHONY: guix-dirs guix-pull-bench guix-pull guix-core guix-dev guix-gc guix-nonguix guix-desktop-common guix-sanctuary-qtile guix-sanctuary-gnustep guix-sanctuary-cde guix-sanctuary-sx guix-room-gaming guix-room-windows-compat guix-room-fvwm95 guix-room-retropie

guix-dirs:
| @chmod +x $(HOME)/.local/bin/guix-mkdirs 2>/dev/null || true
| @$(HOME)/.local/bin/guix-mkdirs
| @mkdir -p $(BENCH_DIR)
# 1) BENCH → writes cache, prints URL (LOUD)
guix-pull-bench: guix-dirs
| set -Eeuo pipefail; \
| BENCH="$(HOME)/DotCortex/all/.local/bin/guix-bench-pull"; \
| [ -x "$$BENCH" ] || { echo "guix-bench-pull not found/executable" >&2; exit 1; }; \
| URL="$$( "$$BENCH" )" || URL=""; \
| if [ -z "$$URL" ]; then echo "No URL found by bench" >&2; exit 1; fi; \
| echo "$$URL" >"$(PULL_CACHE)"; \
| echo "cached: $(PULL_CACHE) → $$URL"; \
| echo "$$URL"

# 2) PULL → uses cached URL if present; NEVER re-bench
guix-pull: guix-dirs
| set -Eeuo pipefail; \
| URL=""; [ -r "$(PULL_CACHE)" ] && URL="$$(tr -d '\r\n' <"$(PULL_CACHE)")"; \
| tried=0; \
| success=0; \
| choose_and_pull() { \
|   u="$$1"; \
|   [ -z "$$u" ] && return 1; \
|   tried=1; \
|   echo "guix pull --url=$$u (cached/fallback)"; \
|   if $(GUIX) pull --url="$$u"; then \
|     success=1; \
|     printf '%s\n' "$$u" >"$(PULL_CACHE)";  # <-- promote last success to cache
|     return 0; \
|   else \
|     return 1; \
|   fi; \
| }; \
| # 1) try cached (if present)
| if [ -n "$$URL" ]; then \
|   choose_and_pull "$$URL" || echo "cached URL failed → trying fallbacks…"; \
| fi; \
| # 2) try fallbacks (skip if equal to cached)
| if [ "$$success" -eq 0 ]; then \
|   for fb in $(FALLBACK_PULL_URLS); do \
|     [ "$$fb" = "$$URL" ] && continue; \
|     if choose_and_pull "$$fb"; then break; fi; \
|   done; \
| fi; \
| # 3) final fallback: plain `guix pull` (no mirror override)
| if [ "$$success" -eq 0 ]; then \
|   if [ "$$tried" -eq 1 ]; then echo "all mirrors failed → falling back to plain 'guix pull'"; else echo "guix pull (no cache present)"; fi; \
|   $(GUIX) pull; \
| fi

guix-core: guix-dirs
| mkdir -p $(EXTRA)/core
| $(GUIX) package -m $(GUIX_HOME)/manifests/core.scm -p $(EXTRA)/core/core

guix-dev: guix-core
| mkdir -p $(EXTRA)/dev
| $(GUIX) package -m $(GUIX_HOME)/manifests/dev.scm -p $(EXTRA)/dev/dev

guix-nonguix: guix-dirs
| mkdir -p $(EXTRA)/nonguix
| $(GUIX) package -m $(GUIX_HOME)/manifests/nonguix.scm -p $(EXTRA)/nonguix/nonguix

# Virtual Habitat — sanctuary substrate profiles (Phase 0B stubs; apply in Phase 1A)
guix-desktop-common: guix-dirs
| mkdir -p $(EXTRA)/desktop-common
| $(GUIX) package -m $(GUIX_HOME)/manifests/desktop-common.scm -p $(EXTRA)/desktop-common/desktop-common

guix-sanctuary-qtile: guix-desktop-common
| mkdir -p $(EXTRA)/sanctuary-qtile
| $(GUIX) package -m $(GUIX_HOME)/manifests/sanctuaries/sanctuary-qtile.scm -p $(EXTRA)/sanctuary-qtile/sanctuary-qtile

guix-sanctuary-gnustep: guix-desktop-common
| mkdir -p $(EXTRA)/sanctuary-gnustep
| $(GUIX) package -m $(GUIX_HOME)/manifests/sanctuaries/sanctuary-gnustep.scm -p $(EXTRA)/sanctuary-gnustep/sanctuary-gnustep

guix-sanctuary-cde: guix-desktop-common
| mkdir -p $(EXTRA)/sanctuary-cde
| $(GUIX) package -L $(LOCAL_PKGS) -m $(GUIX_HOME)/manifests/sanctuaries/sanctuary-cde.scm -p $(EXTRA)/sanctuary-cde/sanctuary-cde

guix-sanctuary-sx: guix-desktop-common
| mkdir -p $(EXTRA)/sanctuary-sx
| $(GUIX) package -m $(GUIX_HOME)/manifests/sanctuaries/sanctuary-sx.scm -p $(EXTRA)/sanctuary-sx/sanctuary-sx

guix-room-gaming: guix-desktop-common
| mkdir -p $(EXTRA)/room-gaming
| $(GUIX) package -m $(GUIX_HOME)/manifests/sanctuaries/room-gaming.scm -p $(EXTRA)/room-gaming/room-gaming

guix-room-windows-compat: guix-desktop-common
| mkdir -p $(EXTRA)/room-windows-compat
| $(GUIX) package -L $(LOCAL_PKGS) -m $(GUIX_HOME)/manifests/sanctuaries/room-windows-compat.scm -p $(EXTRA)/room-windows-compat/room-windows-compat

guix-room-fvwm95: guix-dirs
| mkdir -p $(EXTRA)/room-fvwm95
| $(GUIX) package -m $(GUIX_HOME)/manifests/sanctuaries/room-fvwm95.scm -p $(EXTRA)/room-fvwm95/room-fvwm95

guix-room-retropie: guix-dirs
| mkdir -p $(EXTRA)/room-retropie
| $(GUIX) package -L $(LOCAL_PKGS) -m $(GUIX_HOME)/manifests/sanctuaries/room-retropie.scm -p $(EXTRA)/room-retropie/room-retropie

guix-gc:
| $(GUIX) gc
endif
