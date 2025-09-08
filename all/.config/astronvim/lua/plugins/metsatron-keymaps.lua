return {
  "AstroNvim/astrocore",
  opts = function(_, opts)
    opts.mappings = opts.mappings or {}
    local n = opts.mappings.n or {}

    -- open_config helpers
    local oc = require("metsatron.open_config")
    n["<leader>fe"]  = { oc.pick,                          "Edit Config (picker)" }
    n["<leader>fei"] = { function() oc.open("init.lua") end,                    "Edit init.lua" }
    n["<leader>fel"] = { function() oc.open("lua/metsatron/lazy.lua") end,     "Edit lazy.lua" }
    n["<leader>fek"] = { function() oc.open("lua/metsatron/keymaps.lua") end,  "Edit keymaps.lua" }
    n["<leader>feo"] = { function() oc.open("lua/metsatron/options.lua") end,  "Edit options.lua" }
    n["<leader>fen"] = { function() oc.open("lua/metsatron/neio.lua") end,     "Edit neio.lua" }

    -- NEIO layer toggles
    n["<leader>uN"] = { function() require("metsatron.neio").toggle() end, "Toggle NEIO" }

    -- Bufferline navigation
    n["<leader>bb"] = { "<cmd>BufferLinePick<cr>",                 "Pick Buffer" }
    n["<leader>bp"] = { "<cmd>BufferLineCyclePrev<cr>",            "Prev Buffer" }
    n["<leader>bn"] = { "<cmd>BufferLineCycleNext<cr>",            "Next Buffer" }
    n["<leader>b1"] = { "<cmd>BufferLineGoToBuffer 1<cr>",         "Buffer 1" }
    n["<leader>b2"] = { "<cmd>BufferLineGoToBuffer 2<cr>",         "Buffer 2" }
    n["<leader>b3"] = { "<cmd>BufferLineGoToBuffer 3<cr>",         "Buffer 3" }

    -- Spacemacs vibes
    n["<leader>q"]  = { "<cmd>quit<cr>",                           "Quit" }
    n["<leader>sv"] = { "<cmd>source %<cr>",                       "Source file" }
    n["<leader>fs"] = { "<cmd>write<cr>",                          "Save file" }

    -- Diagnostics
    n["[d"] = { vim.diagnostic.goto_prev, "Prev Diagnostic" }
    n["]d"] = { vim.diagnostic.goto_next, "Next Diagnostic" }
    n["<leader>e"] = { vim.diagnostic.open_float, "Line Diagnostics" }

    -- NEIO window nav
    n["<leader>wn"] = { "<C-w>h", "Win left  (NEIO)" }
    n["<leader>we"] = { "<C-w>j", "Win down  (NEIO)" }
    n["<leader>wi"] = { "<C-w>k", "Win up    (NEIO)" }
    n["<leader>wo"] = { "<C-w>l", "Win right (NEIO)" }

    -- Ctrl-NEIO and arrow fallbacks
    n["<C-n>"]       = { "<C-w>h", "Win left  (Ctrl-NEIO)" }
    n["<C-e>"]       = { "<C-w>j", "Win down  (Ctrl-NEIO)" }
    n["<C-i>"]       = { "<C-w>k", "Win up    (Ctrl-NEIO)" } -- note: <C-i> equals <Tab>
    n["<C-o>"]       = { "<C-w>l", "Win right (Ctrl-NEIO)" }
    n["<C-S-Left>"]  = { "<C-w>h", "Win left  (Ctrl+Shift+Arrow)" }
    n["<C-S-Down>"]  = { "<C-w>j", "Win down  (Ctrl+Shift+Arrow)" }
    n["<C-S-Up>"]    = { "<C-w>k", "Win up    (Ctrl+Shift+Arrow)" }
    n["<C-S-Right>"] = { "<C-w>l", "Win right (Ctrl+Shift+Arrow)" }

    -- Ctrl-W NEIO
    n["<C-w>n"] = { "<C-w>h", "Win left  (Ctrl-W NEIO)", remap = true }
    n["<C-w>e"] = { "<C-w>j", "Win down  (Ctrl-W NEIO)", remap = true }
    n["<C-w>i"] = { "<C-w>k", "Win up    (Ctrl-W NEIO)", remap = true }
    n["<C-w>o"] = { "<C-w>l", "Win right (Ctrl-W NEIO)", remap = true }

    -- Splits and sizing
    n["<leader>wv"] = { "<C-w>v", "Split vertical" }
    n["<leader>ws"] = { "<C-w>s", "Split horizontal" }
    n["<leader>wc"] = { "<C-w>c", "Close window" }
    n["<leader>w="] = { "<C-w>=", "Balance windows" }
    n["<leader>w<"] = { "<cmd>vertical resize -5<cr>", "Narrow width" }
    n["<leader>w>"] = { "<cmd>vertical resize +5<cr>", "Widen width" }
    n["<leader>w-"] = { "<cmd>resize -3<cr>", "Lower height" }
    n["<leader>w+"] = { "<cmd>resize +3<cr>", "Raise height" }

    -- Tabs and fallbacks
    n["<C-PageUp>"]      = { function() if pcall(require,"bufferline") then vim.cmd("BufferLineCyclePrev") else vim.cmd("bprevious") end end, "Prev Tab" }
    n["<C-PageDown>"]    = { function() if pcall(require,"bufferline") then vim.cmd("BufferLineCycleNext") else vim.cmd("bnext") end end,     "Next Tab" }
    n["<C-S-PageUp>"]    = { "<cmd>BufferLineMovePrev<CR>", "Move Tab Left" }
    n["<C-S-PageDown>"]  = { "<cmd>BufferLineMoveNext<CR>", "Move Tab Right" }
    n["<A-Left>"]        = { function() vim.cmd("bprevious") end, "Prev Tab (alt-left)" }
    n["<A-Right>"]       = { function() vim.cmd("bnext") end,     "Next Tab (alt-right)" }
    n["gT"]              = { function() vim.cmd("bprevious") end, "Prev Tab (gT)" }
    n["gt"]              = { function() vim.cmd("bnext") end,     "Next Tab (gt)" }

    opts.mappings.n = n
  end,
}
