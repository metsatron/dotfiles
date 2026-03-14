-- You can share the same content as the vanilla nvim emitter or require a shared module.
local s = {
  bg      = "(eval (lc/s (lc/get 'astronvim 'syntax) :bg))",
  fg      = "(eval (lc/s (lc/get 'astronvim 'syntax) :fg))",
  comment = "(eval (lc/s (lc/get 'astronvim 'syntax) :comment))",
  string  = "(eval (lc/s (lc/get 'astronvim 'syntax) :string))",
  keyword = "(eval (lc/s (lc/get 'astronvim 'syntax) :keyword))",
  type    = "(eval (lc/s (lc/get 'astronvim 'syntax) :type))",
  func    = "(eval (lc/s (lc/get 'astronvim 'syntax) :func))",
  const   = "(eval (lc/s (lc/get 'astronvim 'syntax) :const))",
  error   = "(eval (lc/s (lc/get 'astronvim 'syntax) :error))",
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
