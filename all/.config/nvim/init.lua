-- Sovereign minimal init (no global side effects)
vim.g.mapleader = " "
vim.g.maplocalleader = ","

require("metsatron.options")
require("metsatron.keymaps")
require("metsatron.lazy")
require("metsatron.neio_neo_tree")
require("metsatron.whichkey")

-- NEIO layer
vim.keymap.set("n", "<leader>uN", function() require("metsatron.neio").toggle() end, { desc = "Toggle NEIO" })
require("metsatron.neio").enable()
