# DNF/OpenMandriva Make targets fragment. Requires GNU Make 3.82+.
.RECIPEPREFIX := |
SHELL := /bin/bash

.PHONY: dnf-capture dnf-diff dnf-sync dnf-apply dnf-health dnf-sonicde-xlibre

dnf-capture:
| @chmod +x $(HOME)/.local/bin/dnf-capture 2>/dev/null || true
| $(HOME)/.local/bin/dnf-capture

dnf-diff:
| @chmod +x $(HOME)/.local/bin/dnf-diff 2>/dev/null || true
| $(HOME)/.local/bin/dnf-diff

dnf-sync:
| @chmod +x $(HOME)/.local/bin/dnf-apply 2>/dev/null || true
| UPDATE_FIRST=0 $(HOME)/.local/bin/dnf-apply

dnf-apply:
| @chmod +x $(HOME)/.local/bin/dnf-apply 2>/dev/null || true
| UPDATE_FIRST=1 $(HOME)/.local/bin/dnf-apply

dnf-health:
| @chmod +x $(HOME)/.local/bin/dnf-health 2>/dev/null || true
| $(HOME)/.local/bin/dnf-health

dnf-sonicde-xlibre:
| @chmod +x $(HOME)/.local/bin/openmandriva-sonicde-xlibre 2>/dev/null || true
| $(HOME)/.local/bin/openmandriva-sonicde-xlibre
