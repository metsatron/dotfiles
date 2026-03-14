local s = {
  bg      = "(eval (lc/s (lc/get 'nvim 'syntax) :bg))",
  fg      = "(eval (lc/s (lc/get 'nvim 'syntax) :fg))",
  comment = "(eval (lc/s (lc/get 'nvim 'syntax) :comment))",
  string  = "(eval (lc/s (lc/get 'nvim 'syntax) :string))",
  keyword = "(eval (lc/s (lc/get 'nvim 'syntax) :keyword))",
  type    = "(eval (lc/s (lc/get 'nvim 'syntax) :type))",
  func    = "(eval (lc/s (lc/get 'nvim 'syntax) :func))",
  const   = "(eval (lc/s (lc/get 'nvim 'syntax) :const))",
  error   = "(eval (lc/s (lc/get 'nvim 'syntax) :error))",
}
vim.cmd("hi clear")
vim.g.colors_name = "laincore"
local function hi(g, opts) vim.api.nvim_set_hl(0, g, opts) end
hi("Normal",      { fg = s.fg, bg = s.bg })
hi("Comment",     { fg = s.comment, italic = true })
hi("String",      { fg = s.string })
hi("Keyword",     { fg = s.keyword })
hi("Type",        { fg = s.type })
hi("Function",    { fg = s.func })
hi("Constant",    { fg = s.const })
hi("Error",       { fg = s.error })
