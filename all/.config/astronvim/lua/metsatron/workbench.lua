local M = {}
function M.workbench()
  vim.cmd("Neotree reveal")
  vim.cmd("vsplit")
  vim.cmd("wincmd l")
  vim.cmd("terminal")
end
function M.tree_only()
  vim.cmd("Neotree toggle")
end
return M
