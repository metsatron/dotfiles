-- lua/metsatron/neio_neo_tree.lua
local function feed(keys)
  local k = vim.api.nvim_replace_termcodes(keys, true, false, true)
  vim.api.nvim_feedkeys(k, "n", false)
end

vim.api.nvim_create_autocmd("FileType", {
  pattern = "neo-tree",
  callback = function(ev)
    -- n/e/i/o mirror h/j/k/l INSIDE the tree
    local opts = { buffer = ev.buf, silent = true, nowait = true }
    pcall(vim.keymap.del, "n", "i", { buffer = ev.buf }) -- kill info popup
    pcall(vim.keymap.del, "n", "o", { buffer = ev.buf }) -- kill action menu

    vim.keymap.set("n", "n", function() feed("h") end, opts) -- collapse/parent
    vim.keymap.set("n", "e", function() feed("j") end, opts) -- next
    vim.keymap.set("n", "i", function() feed("k") end, opts) -- prev
    vim.keymap.set("n", "o", function() feed("l") end, opts) -- open/expand
  end,
})
