local M = { enabled = true }
function M.enable() M.enabled = true; vim.notify("NEIO enabled") end
function M.disable() M.enabled = false; vim.notify("NEIO disabled") end
function M.toggle() M.enabled = not M.enabled; vim.notify("NEIO " .. (M.enabled and "enabled" or "disabled")) end
return M
