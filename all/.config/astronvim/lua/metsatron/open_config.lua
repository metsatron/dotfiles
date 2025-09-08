local M = {}

local function root()
  return (vim.env.XDG_CONFIG_HOME or (vim.env.HOME .. "/.config")) .. "/" .. (vim.env.NVIM_APPNAME or "nvim")
end

local files = {
  "init.lua",
  "lua/metsatron/lazy.lua",
  "lua/metsatron/keymaps.lua",
  "lua/metsatron/options.lua",
  "lua/metsatron/neio.lua",
}

function M.pick()
  local items = vim.tbl_map(function(f) return { label = f, path = root() .. "/" .. f } end, files)
  vim.ui.select(items, { prompt = "Open config file" }, function(item)
    if item and item.path then vim.cmd.edit(item.path) end
  end)
end

function M.open(relpath)
  vim.cmd.edit(root() .. "/" .. relpath)
end

return M
