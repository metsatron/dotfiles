local map = function(mode, lhs, rhs, desc)
  vim.keymap.set(mode, lhs, rhs, { silent = true, noremap = true, desc = desc })
end

local oc = require("metsatron.open_config")
map("n", "<leader>fe",  oc.pick,                                   "Edit Config (picker)")
map("n", "<leader>fei", function() oc.open("init.lua") end,        "Edit init.lua")
map("n", "<leader>fel", function() oc.open("lua/metsatron/lazy.lua") end,   "Edit lazy.lua")
map("n", "<leader>fek", function() oc.open("lua/metsatron/keymaps.lua") end,"Edit keymaps.lua")
map("n", "<leader>feo", function() oc.open("lua/metsatron/options.lua") end,"Edit options.lua")
map("n", "<leader>fen", function() oc.open("lua/metsatron/neio.lua") end,   "Edit neio.lua")

-- Bufferline navigation (SWAPPED as requested)
map("n", "<leader>bb", "<cmd>BufferLinePick<cr>",      "Pick Buffer")
map("n", "<leader>bp", "<cmd>BufferLineCyclePrev<cr>", "Prev Buffer")
map("n", "<leader>bn", "<cmd>BufferLineCycleNext<cr>", "Next Buffer")
map("n", "<leader>b1", "<cmd>BufferLineGoToBuffer 1<cr>", "Buffer 1")
map("n", "<leader>b2", "<cmd>BufferLineGoToBuffer 2<cr>", "Buffer 2")
map("n", "<leader>b3", "<cmd>BufferLineGoToBuffer 3<cr>", "Buffer 3")

-- Spacemacs-like habits (leader only; no core hjkl/NEIO changes)
map("n", "<leader>q", "<cmd>quit<cr>",  "Quit")
map("n", "<leader>sv", "<cmd>source %<cr>", "Source file")
map("n", "<leader>fs", "<cmd>write<cr>", "Save file")

-- Diagnostics (native)
map("n", "[d", vim.diagnostic.goto_prev, "Prev Diagnostic")
map("n", "]d", vim.diagnostic.goto_next, "Next Diagnostic")
map("n", "<leader>e", vim.diagnostic.open_float, "Line Diagnostics")

-- nuke any legacy hjkl leader maps that might still exist
for _, k in ipairs({ "h", "j", "k", "l" }) do
  pcall(vim.keymap.del, "n", "<leader>w" .. k)
end

-- Leader window nav (NEIO)
vim.keymap.set("n", "<leader>wn", "<C-w>h", { desc = "Win left  (NEIO)" })
vim.keymap.set("n", "<leader>we", "<C-w>j", { desc = "Win down  (NEIO)" })
vim.keymap.set("n", "<leader>wi", "<C-w>k", { desc = "Win up    (NEIO)" })
vim.keymap.set("n", "<leader>wo", "<C-w>l", { desc = "Win right (NEIO)" })

-- Ctrl-NEIO (letters): most terminals cannot distinguish Ctrl+Shift+letter.
-- We'll add Arrow-based Ctrl+Shift fallbacks which DO work.
vim.keymap.set("n", "<C-n>", "<C-w>h", { desc = "Win left  (Ctrl-NEIO)" })
vim.keymap.set("n", "<C-e>", "<C-w>j", { desc = "Win down  (Ctrl-NEIO)" })
vim.keymap.set("n", "<C-i>", "<C-w>k", { desc = "Win up    (Ctrl-NEIO)" }) -- note: <C-i> == <Tab> in Vim
vim.keymap.set("n", "<C-o>", "<C-w>l", { desc = "Win right (Ctrl-NEIO)" })

-- Arrow fallbacks that preserve Shift modifiers in most terminals
vim.keymap.set("n", "<C-S-Left>",  "<C-w>h", { desc = "Win left  (Ctrl+Shift+Arrow)" })
vim.keymap.set("n", "<C-S-Down>",  "<C-w>j", { desc = "Win down  (Ctrl+Shift+Arrow)" })
vim.keymap.set("n", "<C-S-Up>",    "<C-w>k", { desc = "Win up    (Ctrl+Shift+Arrow)" })
vim.keymap.set("n", "<C-S-Right>", "<C-w>l", { desc = "Win right (Ctrl+Shift+Arrow)" })

-- Ctrl-NEIO (and uppercase / <C-S-…> variants for stubborn terminals)
for _, lhs in ipairs({ "<C-n>", "<C-N>", "<C-S-n>" }) do
  vim.keymap.set("n", lhs, "<C-w>h", { desc = "Win left  (Ctrl-NEIO)" })
end
for _, lhs in ipairs({ "<C-e>", "<C-E>", "<C-S-e>" }) do
  vim.keymap.set("n", lhs, "<C-w>j", { desc = "Win down  (Ctrl-NEIO)" })
end
for _, lhs in ipairs({ "<C-i>", "<C-I>", "<C-S-i>" }) do
  vim.keymap.set("n", lhs, "<C-w>k", { desc = "Win up    (Ctrl-NEIO)" })
end
for _, lhs in ipairs({ "<C-o>", "<C-O>", "<C-S-o>" }) do
  vim.keymap.set("n", lhs, "<C-w>l", { desc = "Win right (Ctrl-NEIO)" })
end

-- Ctrl-W prefix with NEIO (remap so native <C-w> motions execute)
vim.keymap.set("n", "<C-w>n", "<C-w>h", { remap = true, desc = "Win left  (Ctrl-W NEIO)" })
vim.keymap.set("n", "<C-w>e", "<C-w>j", { remap = true, desc = "Win down  (Ctrl-W NEIO)" })
vim.keymap.set("n", "<C-w>i", "<C-w>k", { remap = true, desc = "Win up    (Ctrl-W NEIO)" })
vim.keymap.set("n", "<C-w>o", "<C-w>l", { remap = true, desc = "Win right (Ctrl-W NEIO)" })

-- Splits & sizing (unchanged, but listed)
vim.keymap.set("n", "<leader>wv", "<C-w>v", { desc = "Split vertical" })
vim.keymap.set("n", "<leader>ws", "<C-w>s", { desc = "Split horizontal" })
vim.keymap.set("n", "<leader>wc", "<C-w>c", { desc = "Close window" })
vim.keymap.set("n", "<leader>w=", "<C-w>=", { desc = "Balance windows" })
vim.keymap.set("n", "<leader>w<", "<cmd>vertical resize -5<cr>", { desc = "Narrow width" })
vim.keymap.set("n", "<leader>w>", "<cmd>vertical resize +5<cr>", { desc = "Widen width" })
vim.keymap.set("n", "<leader>w-", "<cmd>resize -3<cr>",          { desc = "Lower height" })
vim.keymap.set("n", "<leader>w+", "<cmd>resize +3<cr>",          { desc = "Raise height" })

local function cycle_prev()
  if pcall(require, "bufferline") then
    vim.cmd("BufferLineCyclePrev")
  else
    vim.cmd("bprevious")
  end
end

local function cycle_next()
  if pcall(require, "bufferline") then
    vim.cmd("BufferLineCycleNext")
  else
    vim.cmd("bnext")
  end
end

-- primary (when terminal supports it)
vim.keymap.set("n", "<C-PageUp>", cycle_prev, { desc = "Prev Tab" })
vim.keymap.set("n", "<C-PageDown>", cycle_next, { desc = "Next Tab" })

-- Move tabs left/right
vim.keymap.set("n", "<C-S-PageUp>",   "<cmd>BufferLineMovePrev<CR>", { desc = "Move Tab Left" })
vim.keymap.set("n", "<C-S-PageDown>", "<cmd>BufferLineMoveNext<CR>", { desc = "Move Tab Right" })

-- extra fallbacks (often work in more terminals)
vim.keymap.set("n", "<A-Left>",  cycle_prev, { desc = "Prev Tab (alt-left)" })
vim.keymap.set("n", "<A-Right>", cycle_next, { desc = "Next Tab (alt-right)" })
vim.keymap.set("n", "gT", cycle_prev, { desc = "Prev Tab (gT)" })
vim.keymap.set("n", "gt", cycle_next, { desc = "Next Tab (gt)" })

local wb = require("metsatron.workbench")
vim.keymap.set("n", "<leader>ow", wb.workbench, { desc = "Workbench (tree + split + terminal)" })
vim.keymap.set("n", "<leader>ot", wb.tree_only,  { desc = "Tree only toggle/reveal" })
