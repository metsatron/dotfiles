# -*- mode: makefile-gmake; indent-tabs-mode: t; tab-width: 8 -*-
.RECIPEPREFIX := |

EMACS ?= emacs
SCRIPT = all/.local/bin/dotfiles-batch.el
ROOT   = $(PWD)
GUIX ?= guix
GUIX_HOME := $(HOME)/.config/guix
EXTRA := $(HOME)/.guix-extra-profiles

# Stow packages you normally manage here
STOW_PKGS ?= all

.PHONY: toc tangle all guix-pull guix-core guix-dev guix-gc guix-dirs \
        stow safe-stow x11-apply bridge-flatpak bridge-flatpak-reset preview-stow lint

lint:
| all/.local/bin/org-style-lint

# Make tangle depend on lint
tangle: lint

# Guix profile sets EMACSLOADPATH without trailing : which hides default lisp paths (cl-lib etc)
export EMACSLOADPATH := $(if $(EMACSLOADPATH),$(addsuffix :,$(EMACSLOADPATH)),)

EMACS_BATCH = $(EMACS) --batch -Q \
  --eval "(setq create-lockfiles nil make-backup-files nil auto-save-default nil backup-inhibited t vc-make-backup-files nil)"

toc:
| $(EMACS_BATCH) --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-update "$(ROOT)")'

tangle:
| $(EMACS_BATCH) --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-tangle "$(ROOT)")'

# all = toc → tangle → guix-dirs only
all: toc tangle guix-dirs

# Plain stow
stow:
| cd $(HOME)/DotCortex && stow $(STOW_PKGS)

# Safe stow with timestamped backups of real files
# LESSON: stow 2.4+ changed conflict message format from:
#   "existing target is neither a link nor a directory: FILE"
# to:
#   "cannot stow PKG/FILE over existing target FILE since neither a link nor a directory"
# We match both patterns plus:
#   "existing target is not owned by stow: FILE"
# If preview reports "existing target is stowed to a different package",
# abort before backing up/removing anything: that target is already repo-owned.
safe-stow:
| set -euo pipefail; \
| cd $(HOME)/DotCortex; \
| repair_mutable_agent_dir() { \
|   local rel="$$1" target="$(HOME)/$$1" resolved entry name rel_entry ts backup; \
|   [ -L "$$target" ] || return 0; \
|   resolved=$$(readlink -f "$$target" 2>/dev/null || true); \
|   echo ">> repair mutable agent dir $$target"; \
|   rm -f "$$target"; \
|   mkdir -p "$$target"; \
|   [ -n "$$resolved" ] && [ -d "$$resolved" ] || return 0; \
|   for entry in "$$resolved"/* "$$resolved"/.[!.]* "$$resolved"/..?*; do \
|     [ -e "$$entry" ] || [ -L "$$entry" ] || continue; \
|     name=$$(basename "$$entry"); \
|     rel_entry=$${entry#$(HOME)/DotCortex/}; \
|     if git ls-files --error-unmatch "$$rel_entry" >/dev/null 2>&1 || git ls-files "$$rel_entry/" | grep -q .; then \
|       continue; \
|     fi; \
|     if [ -e "$$target/$$name" ] || [ -L "$$target/$$name" ]; then \
|       ts=$$(date +%Y%m%d-%H%M%S); \
|       backup="$$target/$$name.bak.$$ts"; \
|       echo "   backup existing $$target/$$name -> $$backup"; \
|       mv "$$target/$$name" "$$backup"; \
|     fi; \
|     echo "   move runtime $$entry -> $$target/$$name"; \
|     mv "$$entry" "$$target/$$name"; \
|   done; \
| }; \
| repair_mutable_agent_dir .claude; \
| repair_mutable_agent_dir .agents; \
| repair_mutable_agent_dir .opencode; \
| repair_mutable_agent_dir .codex; \
| for pkg in $(STOW_PKGS); do \
|   preview_file=$$(mktemp); \
|   echo ">> preview $$pkg"; \
|   stow -n --ignore='\.bak\.' $$pkg >"$$preview_file" 2>&1 || true; \
|   if grep -q 'existing target is stowed to a different package:' "$$preview_file"; then \
|     cat "$$preview_file"; \
|     rm -f "$$preview_file"; \
|     exit 1; \
|   fi; \
|   sed -n \
|       -e 's/.*existing target is neither a link nor a directory: \(.*\)$$/\1/p' \
|       -e 's/.*over existing target \(.*\) since neither.*/\1/p' \
|       -e 's/.*existing target is not owned by stow: \(.*\)$$/\1/p' \
|       "$$preview_file" \
|     | { grep -v '^HelmCortex$$' || true; } \
|     | while read -r t; do \
|         case "$$t" in /*) abs="$$t" ;; *) abs="$(HOME)/$$t" ;; esac; \
|         if [ -e "$$abs" ] || [ -L "$$abs" ]; then \
|           if [ "$$t" = ".config/opencode/opencode.json" ]; then \
|             HELPER="$(HOME)/.local/bin/dotcortex-opencode-config-merge-guard"; \
|             [ -x "$$HELPER" ] || HELPER="$(HOME)/DotCortex/all/.local/bin/dotcortex-opencode-config-merge-guard"; \
|             if [ -x "$$HELPER" ]; then \
|               "$$HELPER" apply; \
|               continue; \
|             fi; \
|           fi; \
|           ts=$$(date +%Y%m%d-%H%M%S); \
|           echo "   backup $$abs -> $$abs.bak.$$ts"; \
|           cp -a "$$abs" "$$abs.bak.$$ts"; \
|           echo "   remove  $$abs"; \
|           rm -rf "$$abs"; \
|         fi; \
|       done; \
|   rm -f "$$preview_file"; \
|   echo ">> stow $$pkg"; \
|   if stow --ignore='\.bak\.' $$pkg 2>&1; then \
|     true; \
|   else \
|     echo ">> stow $$pkg conflict — retrying with --ignore=HelmCortex"; \
|     stow --ignore='HelmCortex' --ignore='\.bak\.' $$pkg; \
|   fi; \
| done; \
| case " $(STOW_PKGS) " in \
|   *" all "*|*" linux "*) \
|     HELPER="$(HOME)/.local/bin/icons-home-sync"; \
|     [ -x "$$HELPER" ] || HELPER="$(HOME)/DotCortex/all/.local/bin/icons-home-sync"; \
|     if [ -x "$$HELPER" ]; then \
|       echo ">> icons-sync"; \
|       "$$HELPER"; \
|     fi; \
|     ;; \
| esac

preview-stow:
| cd $(HOME)/DotCortex && stow -n $(STOW_PKGS) || true

# X11 apply for x230 overlay
x11-apply: tangle
| cd $(HOME)/DotCortex && stow x230
| @echo "✅ X11 applied."

include $(HOME)/DotCortex/all/.mk/flatpak.mk
include $(HOME)/DotCortex/all/.mk/icons.mk
include $(HOME)/DotCortex/all/.mk/guix.mk
include $(HOME)/DotCortex/all/.mk/guix-substitutes.mk
include $(HOME)/DotCortex/all/.mk/agent-guix.mk
include $(HOME)/DotCortex/all/.mk/snap.mk
include $(HOME)/DotCortex/all/.mk/appimage.mk
include $(HOME)/DotCortex/all/.mk/am.mk
include $(HOME)/DotCortex/all/.mk/cargo.mk
include $(HOME)/DotCortex/all/.mk/homebrew.mk
include $(HOME)/DotCortex/all/.mk/bun.mk
include $(HOME)/DotCortex/all/.mk/bunx.mk
include $(HOME)/DotCortex/all/.mk/npm.mk
include $(HOME)/DotCortex/all/.mk/pip.mk
include $(HOME)/DotCortex/all/.mk/pipx.mk
include $(HOME)/DotCortex/all/.mk/nala.mk
include $(HOME)/DotCortex/all/.mk/dnf.mk
include $(HOME)/DotCortex/all/.mk/bots.mk
include $(HOME)/DotCortex/all/.mk/sessions.mk
include $(HOME)/DotCortex/all/.mk/termux.mk
include $(HOME)/DotCortex/all/.mk/plasmoid.mk
