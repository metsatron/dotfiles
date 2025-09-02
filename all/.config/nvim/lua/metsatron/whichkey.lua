-- lua/metsatron/whichkey.lua
local ok, wk = pcall(require, "which-key")
if not ok then return end

wk.add({
  { "<leader>b", group = "buffer" },
  { "<leader>f", group = "file" },
  { "<leader>o", group = "open" },
  { "<leader>s", group = "source" },
  { "<leader>w", group = "window" },
  { "<leader>u", group = "utility" },
}, { mode = "n" })
