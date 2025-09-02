local o = vim.opt

o.number = true
o.relativenumber = false
o.mouse = "a"
o.clipboard = "unnamedplus"
o.breakindent = true
o.smartindent = true
o.ignorecase = true
o.smartcase = true
o.signcolumn = "yes"
o.updatetime = 200
o.timeoutlen = 400
o.termguicolors = true
o.scrolloff = 4
o.sidescrolloff = 4
o.splitright = true
o.splitbelow = true

vim.g.loaded_node_provider = 0
vim.g.loaded_ruby_provider = 0
vim.g.loaded_perl_provider = 0

-- in lua/metsatron/options.lua (or anywhere global)
vim.opt.expandtab   = true  -- tabs become spaces
vim.opt.shiftwidth  = 2     -- how many spaces to indent with > and <
vim.opt.tabstop     = 2
vim.opt.softtabstop = 2

-- keep selection after indent/outdent
vim.keymap.set("v", ">", ">gv", { desc = "Indent and keep selection" })
vim.keymap.set("v", "<", "<gv", { desc = "Outdent and keep selection" })
