-- lua/metsatron/workbench.lua
local M = {}

local function is_tree(win)
  local b = vim.api.nvim_win_get_buf(win)
  return vim.bo[b].filetype == "neo-tree"
end

local function is_term(win)
  local b = vim.api.nvim_win_get_buf(win)
  return vim.bo[b].buftype == "terminal"
end

local function any_editor_win()
  for _, w in ipairs(vim.api.nvim_list_wins()) do
    local b = vim.api.nvim_win_get_buf(w)
    if vim.bo[b].filetype ~= "neo-tree" and vim.bo[b].buftype ~= "terminal" then
      return w
    end
  end
end

local function focus(win) if win then vim.api.nvim_set_current_win(win) end end

local function show_tree_left()
  vim.cmd("Neotree show left")
  -- return the tree window
  for _, w in ipairs(vim.api.nvim_list_wins()) do if is_tree(w) then return w end end
end

local function goto_left_editor_from_tree(tree_win)
  -- from tree, step one to the right = left editor column
  vim.api.nvim_set_current_win(tree_win)
  vim.cmd("wincmd l")
  return vim.api.nvim_get_current_win()
end

local function ensure_two_editor_columns(left_editor_win)
  -- if we only have one editor column, vsplit to make a right column
  local editors = {}
  for _, w in ipairs(vim.api.nvim_list_wins()) do
    local b = vim.api.nvim_win_get_buf(w)
    if vim.bo[b].filetype ~= "neo-tree" and vim.bo[b].buftype ~= "terminal" then
      table.insert(editors, w)
    end
  end
  if #editors < 2 then
    vim.api.nvim_set_current_win(left_editor_win)
    vim.cmd("vertical rightbelow vsplit")
    -- new window is right editor; keep both
  end
end

local function ensure_terminal_below_left_editor(left_editor_win)
  -- go to left editor, create/ensure a terminal below, height ~10
  vim.api.nvim_set_current_win(left_editor_win)
  -- check if there is already a terminal below (simplify: always enforce)
  vim.cmd("belowright split")
  if not is_term(vim.api.nvim_get_current_win()) then
    vim.cmd("terminal")
    vim.cmd("stopinsert")
  end
  vim.cmd("resize 10")
end

function M.tree_only()
  vim.cmd("Neotree toggle reveal left")
end

function M.workbench()
  -- 1) tree left
  local tree = show_tree_left()
  vim.wo[tree].winfixwidth = true

  -- 2) make sure we have at least one editor
  if not any_editor_win() then
    local cur = goto_left_editor_from_tree(tree)
    vim.cmd("enew")
  end

  -- 3) left editor = immediate right of tree
  local left_editor = goto_left_editor_from_tree(tree)

  -- 4) ensure right editor column exists
  ensure_two_editor_columns(left_editor)

  -- 5) ensure terminal is *below the left editor* (middle column bottom)
  ensure_terminal_below_left_editor(left_editor)

  -- 6) finish focused on right editor
  -- hop to the right-most non-tree, non-terminal window
  for _ = 1, 3 do vim.cmd("wincmd l") end
  -- if that landed on terminal by chance, one more hop right
  if is_term(vim.api.nvim_get_current_win()) then vim.cmd("wincmd l") end
end

return M
