ifndef NONGUIX_SUBS_MK_INCLUDED
NONGUIX_SUBS_MK_INCLUDED := 1

.RECIPEPREFIX := |
SHELL := /bin/bash
.ONESHELL:

BENCH_DIR := $(HOME)/.config/guix/.bench
NONGUIX_SUB_CACHE := $(BENCH_DIR)/nonguix-substitute-order

.PHONY: nonguix-sub-bench nonguix-sub-apply nonguix-authorize-key

nonguix-sub-bench:
| set -Eeuo pipefail; \
| mkdir -p "$(BENCH_DIR)"; \
| ORDER="$$( GUIX_SUB_CANDIDATES='https://substitutes.nonguix.org https://bordeaux.guix.gnu.org https://ci.guix.gnu.org' \
|            ~/.local/bin/guix-bench-substitutes | awk 'NF{last=$$0} END{print last}' )"; \
| if [ -z "$$ORDER" ]; then echo "No ORDER from bench" >&2; exit 1; fi; \
| echo "$$ORDER" >"$(NONGUIX_SUB_CACHE)"; \
| echo "cached: $(NONGUIX_SUB_CACHE) → $$ORDER"; \
| echo "$$ORDER"

nonguix-sub-apply:
| set -Eeuo pipefail; \
| [ -r "$(NONGUIX_SUB_CACHE)" ] || { echo "No $(NONGUIX_SUB_CACHE). Run 'make -f all/.mk/nonguix-substitutes.mk nonguix-sub-bench' first." >&2; exit 1; }; \
| ORDER="$$(tr -d '\r\n' <"$(NONGUIX_SUB_CACHE)")"; \
| if [ -z "$$ORDER" ]; then echo "Empty $(NONGUIX_SUB_CACHE)" >&2; exit 1; fi; \
| DAEMON_BIN="$$(systemctl show -p ExecStart guix-daemon 2>/dev/null | sed -E 's/^ExecStart=..([^ ]*guix-daemon).*/\1/')"; \
| [ -z "$$DAEMON_BIN" -o ! -x "$$DAEMON_BIN" ] && DAEMON_BIN="/var/guix/profiles/per-user/root/current-guix/bin/guix-daemon"; \
| sudo mkdir -p /etc/systemd/system/guix-daemon.service.d; \
| tmp="$$(mktemp)"; \
| printf '%s\n' \
|   "[Service]" \
|   "Environment=GUIX_LOCPATH=/var/guix/profiles/per-user/root/guix-profile/lib/locale" \
|   "ExecStart=" \
|   "ExecStart=$$DAEMON_BIN --build-users-group=guixbuild --substitute-urls=\"$$ORDER\"" \
|   > "$$tmp"; \
| sudo install -m 0644 "$$tmp" /etc/systemd/system/guix-daemon.service.d/override.conf; \
| rm -f "$$tmp"; \
| sudo systemctl daemon-reload; \
| sudo systemctl restart guix-daemon; \
| systemctl --no-pager status guix-daemon || true

nonguix-authorize-key:
| set -Eeuo pipefail; \
| if [ -r /usr/share/guix/nonguix.pub ]; then key=/usr/share/guix/nonguix.pub; \
| elif [ -r /etc/guix/nonguix.pub ]; then key=/etc/guix/nonguix.pub; \
| elif [ -r $(HOME)/DotCortex/all/.config/guix/nonguix-signing-key.pub ]; then key=$(HOME)/DotCortex/all/.config/guix/nonguix-signing-key.pub; \
| else echo "WARNING: nonguix key not found. Put it at all/.config/guix/nonguix-signing-key.pub and rerun." >&2; exit 0; fi; \
| echo "Authorizing nonguix key: $$key"; \
| sudo guix archive --authorize < "$$key"
endif
