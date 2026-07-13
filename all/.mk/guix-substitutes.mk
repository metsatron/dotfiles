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
| \
| # Thermal guard, same marker the cargo lane honours. A host that cannot survive \
| # a compile does not get to run one, and the refusal belongs in the tool, not in \
| # an agent's good intentions. --max-jobs=0 forbids LOCAL build jobs outright: \
| # every derivation must arrive as a substitute or be offloaded to a build machine \
| # (/etc/guix/machines.scm). Without it the daemon cheerfully compiles locally the \
| # moment a substitute misses -- and the custom packages defined in this very file \
| # (patched gvfs, emulationstation, ...) NEVER have an upstream substitute, so the \
| # miss is guaranteed, not hypothetical. That is how the X230 hardware-thermal-killed \
| # itself on 2026-07-13, taking the fleet's NFS/Samba/ZFS with it. \
| # This must live HERE rather than as a hand-edit of override.conf, because this \
| # recipe REGENERATES override.conf -- a hand-edit would be silently wiped on the \
| # next guix-sub-apply, which is precisely the silent-drift class we keep paying for. \
| EXTRA=""; \
| if [[ -e "$$HOME/.config/dotcortex/no-local-builds" ]]; then \
|   EXTRA=" --max-jobs=0"; \
|   echo ">> $$(hostname): marked no-local-builds — daemon gets --max-jobs=0 (substitute or offload only)"; \
| fi; \
| sudo mkdir -p /etc/systemd/system/guix-daemon.service.d; \
| tmp="$$(mktemp)"; \
| printf '%s\n[Service]\nEnvironment=GUIX_LOCPATH=/var/guix/profiles/per-user/root/guix-profile/lib/locale\nExecStart=\nExecStart=%s --build-users-group=guixbuild%s --substitute-urls=\"%s\"\n' \
|   "" "$$DAEMON_BIN" "$$EXTRA" "$$SUB_URLS" >"$$tmp"; \
| sudo install -m 0644 "$$tmp" /etc/systemd/system/guix-daemon.service.d/override.conf; rm -f "$$tmp"; \
| sudo systemctl daemon-reload; sudo systemctl restart guix-daemon; \
| systemctl --no-pager status guix-daemon || true
endif
