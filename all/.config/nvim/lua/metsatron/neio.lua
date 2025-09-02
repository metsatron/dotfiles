-- lua/metsatron/neio.lua
-- NEIO "literal": motions on n/e/i/o; insert/open moved to k/l
local M, enabled = {}, false

local function map(modes, lhs, rhs, desc)
  vim.keymap.set(modes, lhs, rhs, { noremap = true, silent = true, desc = desc })
end
local function del(modes, lhs)
  pcall(vim.keymap.del, modes, lhs)
end

function M.enable()
  if enabled then return end

  -- 1) hard-disable hjkl in normal/visual/operator to avoid drift
  for _,mode in ipairs({"n","x","o"}) do
    for _,k in ipairs({"h","j","k","l"}) do
      del(mode, k); map(mode, k, "<Nop>")
    end
  end

  -- search repeat on h/H (normal only)
  vim.keymap.set("n", "h", "n", { noremap = true, silent = true, desc = "Search next" })
  vim.keymap.set("n", "H", "N", { noremap = true, silent = true, desc = "Search prev" })

  -- 2) motions on NEIO (normal/visual/operator)
  map({"n","x","o"}, "n", "h", "NEIO: left")
  map({"n","x","o"}, "e", "j", "NEIO: down")
  map({"n","x","o"}, "i", "k", "NEIO: up")
  map({"n","x","o"}, "o", "l", "NEIO: right")

  -- 3) literal edits: make k/l act like original i/o
  map("n", "k", "i", "NEIO: insert")
  map("n", "K", "I", "NEIO: insert at BOL")
  map("n", "l", "o", "NEIO: open line below")
  map("n", "L", "O", "NEIO: open line above")

  enabled = true
  vim.notify("NEIO literal: enabled", vim.log.levels.INFO)
end

function M.disable()
  if not enabled then return end
  for _,mode in ipairs({"n","x","o"}) do
    for _,k in ipairs({"n","e","i","o","h","j","k","l"}) do
      del(mode, k)
    end
  end
  enabled = false
  vim.notify("NEIO literal: disabled", vim.log.levels.INFO)
end

function M.toggle() if enabled then M.disable() else M.enable() end end
return M
