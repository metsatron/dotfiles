local o = vim.opt

o.number = true
o.relativenumber = false
o.mouse = "a"
o.clipboard = "unnamedplus"

-- Over SSH there is no local display clipboard, so a yank on a remote host
-- never reached the machine in front of him. Copy goes to the terminal's own
-- clipboard with OSC 52 (kitty accepts it); paste reads the unnamed register
-- and never asks the terminal, because most terminals do not answer a
-- clipboard read and the query would hang.
if vim.env.SSH_TTY or vim.env.SSH_CONNECTION then
  local osc52 = require("vim.ui.clipboard.osc52")
  local function paste_from_register()
    return { vim.fn.split(vim.fn.getreg('"'), "\n"), vim.fn.getregtype('"') }
  end
  vim.g.clipboard = {
    name = "OSC 52 copy, register paste",
    copy = { ["+"] = osc52.copy("+"), ["*"] = osc52.copy("*") },
    paste = { ["+"] = paste_from_register, ["*"] = paste_from_register },
  }
end
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
