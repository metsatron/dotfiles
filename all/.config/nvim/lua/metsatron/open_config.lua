local M = {}
local cfg = vim.fn.expand("~/.dotfiles/all/.config/nvim")

function M.pick()
  local ok, tb = pcall(require, "telescope.builtin")
  if ok then
    tb.find_files({ cwd = cfg, prompt_title = "Edit Neovim Config" })
  else
    local files = {
      "init.lua",
      "lua/metsatron/lazy.lua",
      "lua/metsatron/keymaps.lua",
      "lua/metsatron/options.lua",
      "lua/metsatron/neio.lua",
      ".luarc.json",
    }
    vim.ui.select(files, { prompt = "Open config file:" }, function(item)
      if item then vim.cmd.edit(cfg .. "/" .. item) end
    end)
  end
end

function M.open(rel) vim.cmd.edit(cfg .. "/" .. rel) end
return M
