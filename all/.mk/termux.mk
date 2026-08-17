# ~/DotCortex/all/.mk/termux.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: termux-pkg-apply termux-pkg-health termux-piper-apply termux-enclave-apply termux-tts-health termux-defuse-check termux-rish-apply termux-defuse-apply termux-services-apply termux-kitten-apply

termux-pkg-apply:
| @chmod +x $(HOME)/.local/bin/termux-pkg-apply 2>/dev/null || true
| $(HOME)/.local/bin/termux-pkg-apply

termux-pkg-health:
| @chmod +x $(HOME)/.local/bin/termux-pkg-health 2>/dev/null || true
| $(HOME)/.local/bin/termux-pkg-health

termux-piper-apply:
| $(HOME)/.local/bin/termux-piper-apply

termux-enclave-apply:
| $(HOME)/.local/bin/termux-enclave-apply

termux-tts-health:
| @$(HOME)/.local/bin/termux-tts-say "Voice check from the phone stack." || echo "tts not ready — run termux-piper-apply and place a voice model"

termux-defuse-check:
| $(HOME)/.local/bin/termux-defuse-check

termux-rish-apply:
| $(HOME)/.local/bin/termux-rish-apply

termux-defuse-apply:
| $(HOME)/.local/bin/termux-defuse-apply

termux-services-apply:
| $(HOME)/.local/bin/termux-services-apply

termux-kitten-apply:
| $(HOME)/.local/bin/termux-kitten-apply
