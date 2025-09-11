# 🛠️ Make Targets

# [[file:README.org::*🛠️ Make Targets][🛠️ Make Targets:1]]
EMACS ?= emacs
SCRIPT = all/.local/bin/dotfiles-batch.el
ROOT   = $(PWD)

.PHONY: toc tangle all
toc:
	$(EMACS) --batch -Q --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-update "$(ROOT)")'

tangle:
	$(EMACS) --batch -Q --eval '(load-file "$(SCRIPT)")' --eval '(dotfiles-batch-tangle "$(ROOT)")'

all: toc tangle
# 🛠️ Make Targets:1 ends here
