.PHONY: kde1-history-import
kde1-history-import:
	@HELPER="$(HOME)/.local/bin/redstone-9x-kde1-history-import"; \
	if [ ! -x "$$HELPER" ]; then HELPER="$(HOME)/DotCortex/linux/.local/bin/redstone-9x-kde1-history-import"; fi; \
	"$$HELPER" "$${KDE1_SOURCE_REPO:?set KDE1_SOURCE_REPO to the verified kde1-kdebase checkout}" --repo-root "$(HOME)/DotCortex"
