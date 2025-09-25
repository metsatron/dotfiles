# Guix substitutes (bench caches order; apply reads cache only)

# [[file:../../guix.org::*Guix substitutes (bench caches order; apply reads cache only)][Guix substitutes (bench caches order; apply reads cache only):1]]
# all/.mk/guix-substitutes.mk
ifndef GUIX_SUB_MK_INCLUDED
GUIX_SUB_MK_INCLUDED := 1

.RECIPEPREFIX := |
SHELL := /bin/bash
.ONESHELL:

GUIX ?= guix
GUIX_HOME := $(HOME)/.config/guix
BENCH_DIR := $(GUIX_HOME)/.bench
ORDER_CACHE := $(BENCH_DIR)/substitute-order

# Your full candidate list (order here doesn’t matter; bench will pick & cache)
SUB_CANDIDATES ?= \
  https://bordeaux.guix.gnu.org \
  https://ci.guix.gnu.org \
  https://substitutes.nonguix.org \
  https://hydra-guix-129.guix.gnu.org \
  https://berlin-guix.jing.rocks \
  https://bordeaux-guix.jing.rocks \
  https://mirrors.sjtug.sjtu.edu.cn/guix \
  https://mirror.yandex.ru/mirrors/guix/ \
  https://bordeaux-singapore-mirror.cbaines.net \
  https://bordeaux-us-east-mirror.cbaines.net

.PHONY: guix-sub-bench guix-sub-apply

guix-sub-bench:
| set -Eeuo pipefail; \
| mkdir -p "$(BENCH_DIR)"; \
| GUIX_SUB_CANDIDATES="$(SUB_CANDIDATES)" \
|   "$(HOME)/.local/bin/guix-bench-substitutes" \
|   | awk 'NF{last=$$0} END{print last}' >"$(ORDER_CACHE)"; \
| if [ ! -s "$(ORDER_CACHE)" ]; then echo "No ORDER from bench" >&2; exit 1; fi; \
| echo "cached: $(ORDER_CACHE) → $$(cat "$(ORDER_CACHE)")"; \
| cat "$(ORDER_CACHE)"

# Uses cached order only (no re-bench). Same as your good version.
guix-sub-apply:
| set -Eeuo pipefail; \
| [ -r "$(ORDER_CACHE)" ] || { echo "No $(ORDER_CACHE). Run 'guix-sub-bench' first." >&2; exit 1; }; \
| ORDER="$$(tr -d '\r\n' <"$(ORDER_CACHE)")"; \
| [ -n "$$ORDER" ] || { echo "Empty $(ORDER_CACHE)" >&2; exit 1; }; \
| DAEMON_BIN="$$(systemctl show -p ExecStart guix-daemon 2>/dev/null | sed -E 's/^ExecStart=..([^ ]*guix-daemon).*/\1/')"; \
| if [ -z "$$DAEMON_BIN" ] || [ ! -x "$$DAEMON_BIN" ]; then DAEMON_BIN="/var/guix/profiles/per-user/root/current-guix/bin/guix-daemon"; fi; \
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

endif
# Guix substitutes (bench caches order; apply reads cache only):1 ends here
