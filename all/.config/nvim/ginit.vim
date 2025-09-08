" ~/.config/nvim/ginit.vim

" If running in Neovide, use the guifont option
if exists('g:neovide')
  " escape spaces with backslashes or use :h guifont syntax
  set guifont=SFMono\ Nerd\ Font\ Mono:h11
elseif exists(':GuiFont')
  " If running in neovim-qt, use its GuiFont command
  GuiFont SFMono\ Nerd\ Font\ Mono:h11
endif
