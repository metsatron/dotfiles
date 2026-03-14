ifndef GUIX_SUB_MK_INCLUDED
GUIX_SUB_MK_INCLUDED := 1
.RECIPEPREFIX := |
SHELL := /bin/bash
.ONESHELL:

GUIX_HOME := $(HOME)/.config/guix
BENCH_DIR := $(GUIX_HOME)/.bench
ORDER_CACHE := $(BENCH_DIR)/substitute-order

# Full candidate set (bench decides)
SUB_CANDS = "https://bordeaux.guix.gnu.org https://ci.guix.gnu.org https://substitutes.nonguix.org https://hydra-guix-129.guix.gnu.org https://mirrors.sjtug.sjtu.edu.cn/guix https://mirror.yandex.ru/mirrors/guix/ https://bordeaux-singapore-mirror.cbaines.net https://bordeaux-us-east-mirror.cbaines.net"

.PHONY: guix-sub-bench guix-sub-apply

guix-sub-bench:
| set -Eeuo pipefail; \
| mkdir -p "$(BENCH_DIR)"; \
| ORDER="$$( GUIX_SUB_CANDIDATES=$(SUB_CANDS) ~/.local/bin/guix-bench-substitutes )" || { echo "bench failed"; exit 1; }; \
| if ! grep -Eq 'https?://[^ ]+' <<<"$$ORDER"; then echo "bench produced no URLs"; exit 1; fi; \
| printf '%s\n' "$$ORDER" >"$(ORDER_CACHE)"; \
| echo "cached: $(ORDER_CACHE) → $$ORDER"

guix-sub-apply:
| set -Eeuo pipefail; \
| [ -s "$(ORDER_CACHE)" ] || { echo "No $(ORDER_CACHE). Run 'guix-sub-bench' first." >&2; exit 1; }; \
| ORDER="$$(tr -d '\r\n' <"$(ORDER_CACHE)")"; \
| grep -Eq 'https?://[^ ]+' <<<"$$ORDER" || { echo "Invalid ORDER in cache"; exit 1; }; \
| \
| # Start from bench result, then append full candidate list, then dedup. \
| CANDS=$(SUB_CANDS); \
| CANDS="$${CANDS#\"}"; CANDS="$${CANDS%\"}"; \
| SUB_URLS="$$ORDER $$CANDS"; \
| SUB_URLS="$$(printf '%s\n' $$SUB_URLS | awk '!seen[$$0]++' | tr '\n' ' ')"; \
| \
| DAEMON_BIN="$$(systemctl show -p ExecStart guix-daemon 2>/dev/null | sed -E 's/^ExecStart=..([^ ]*guix-daemon).*/\1/')"; \
| [[ -x "$$DAEMON_BIN" ]] || DAEMON_BIN="/var/guix/profiles/per-user/root/current-guix/bin/guix-daemon"; \
| sudo mkdir -p /etc/systemd/system/guix-daemon.service.d; \
| tmp="$$(mktemp)"; \
| printf '%s\n[Service]\nEnvironment=GUIX_LOCPATH=/var/guix/profiles/per-user/root/guix-profile/lib/locale\nExecStart=\nExecStart=%s --build-users-group=guixbuild --substitute-urls=\"%s\"\n' \
|   "" "$$DAEMON_BIN" "$$SUB_URLS" >"$$tmp"; \
| sudo install -m 0644 "$$tmp" /etc/systemd/system/guix-daemon.service.d/override.conf; rm -f "$$tmp"; \
| sudo systemctl daemon-reload; sudo systemctl restart guix-daemon; \
| systemctl --no-pager status guix-daemon || true
endif
