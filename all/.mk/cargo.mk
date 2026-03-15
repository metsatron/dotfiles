# ~/DotCortex/all/.mk/cargo.mk
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: cargo-capture cargo-diff cargo-sync cargo-apply cargo-health

cargo-capture:
| @chmod +x $(HOME)/.local/bin/cargo-capture 2>/dev/null || true
| $(HOME)/.local/bin/cargo-capture

cargo-diff:
| @chmod +x $(HOME)/.local/bin/cargo-diff 2>/dev/null || true
| $(HOME)/.local/bin/cargo-diff

# Install anything new from the manifest, do not uninstall extras, do not rebuild existing.
cargo-sync:
| @chmod +x $(HOME)/.local/bin/cargo-apply 2>/dev/null || true
| ENFORCE=0 UNINSTALL=0 UPDATE=0 $(HOME)/.local/bin/cargo-apply

# Strict apply: install, upgrade, and uninstall extras.
cargo-apply:
| @chmod +x $(HOME)/.local/bin/cargo-apply 2>/dev/null || true
| ENFORCE=1 UNINSTALL=1 UPDATE=1 $(HOME)/.local/bin/cargo-apply

cargo-health:
| @chmod +x $(HOME)/.local/bin/cargo-health 2>/dev/null || true
| $(HOME)/.local/bin/cargo-health
