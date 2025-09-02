-- Bootstrap lazy.nvim (local, no PATH edits)
-- t
local fn = vim.fn
local lazypath = fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  fn.system({ "git", "clone", "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git", "--branch=stable", lazypath })
end
vim.opt.rtp:prepend(lazypath)

local plugins = {
  { "folke/which-key.nvim", opts = {} },

  -- Core libs/UI
  { "nvim-lua/plenary.nvim" },
  { "nvim-tree/nvim-web-devicons", lazy = true },

{
  "nvim-lualine/lualine.nvim",
  dependencies = { "nvim-tree/nvim-web-devicons" },
  opts = function()
    local P = {
      bg      = "#1e1e1e",
      bg_dim  = "#363636",
      fg      = "#ECECEC",
      gray    = "#A0A0A0",
      blue    = "#8CCEFF",
      green   = "#B9F27C",
      yellow  = "#FFD76E",
      red     = "#FF6E6E",
      purple  = "#D4AFFF",
      cyan    = "#7DE1FF",
    }

  opts = {
    options = { theme = "auto", section_separators = "", component_separators = "" },
    sections = {
      lualine_a = { "mode" },
      lualine_b = { "branch" },
      lualine_c = { "filename" },
      lualine_x = { lsp_names, "encoding", "fileformat", "filetype" },
      lualine_y = { "progress" },
      lualine_z = { "location" },
    },
  }

    -- Obsidian-y theme for lualine
    local obsidian = {
      normal  = { a = { fg = P.bg,  bg = P.blue,   gui = "bold" }, b = { fg = P.fg, bg = P.bg_dim }, c = { fg = P.fg, bg = P.bg } },
      insert  = { a = { fg = P.bg,  bg = P.green,  gui = "bold" } },
      visual  = { a = { fg = P.bg,  bg = P.purple, gui = "bold" } },
      replace = { a = { fg = P.bg,  bg = P.red,    gui = "bold" } },
      command = { a = { fg = P.bg,  bg = P.yellow, gui = "bold" } },
      inactive= { a = { fg = P.gray,bg = P.bg },   b = { fg = P.gray,bg = P.bg }, c = { fg = P.gray,bg = P.bg } },
    }

    -- lualine component: show attached LSPs for current buffer (0.11/0.12 safe)
    local function lsp_names()
      local bufnr = vim.api.nvim_get_current_buf()
      local get_clients = vim.lsp.get_clients or vim.lsp.get_active_clients
      local clients = get_clients and (vim.lsp.get_clients and get_clients({ buf = bufnr }) or get_clients()) or {}
      if not clients or vim.tbl_isempty(clients) then return "" end
      local names = {}
      for _, c in ipairs(clients) do
        if not c.config or not c.config.workspace_folders or vim.lsp.buf_is_attached(bufnr, c.id) then
          table.insert(names, c.name)
        end
      end
      return (#names > 0) and ("  " .. table.concat(names, ",")) or ""
    end

    local function cwd() return " " .. vim.fn.fnamemodify(vim.fn.getcwd(), ":t") end

    return {
      options = {
        theme = obsidian,
        globalstatus = true,
        component_separators = { left = "", right = "" },
        section_separators = { left = '', right = '' }, -- ← the “powerline” chevrons
        disabled_filetypes = { statusline = { "neo-tree" } },
        always_divide_middle = true,
      },
      sections = {
        lualine_a = { { "mode", fmt = function(s) return s:gsub("^%l", string.upper) end } },
        lualine_b = { { "branch", icon = "" }, { "diff" } },
        lualine_c = {
          { cwd, separator = { right = "" }, padding = { left = 1, right = 1 } },
          { "filetype", icon_only = true, separator = "", padding = { left = 1, right = 0 } },
          { "filename", path = 1, symbols = { modified = " ●", readonly = " ", unnamed = " [No Name]" } },
          { "diagnostics" },
        },
        lualine_x = { { lsp_names }, "encoding", "fileformat" },
        lualine_y = { "progress" },
        lualine_z = { "location" },
      },
      inactive_sections = {
        lualine_a = {}, lualine_b = {},
        lualine_c = { { "filename", path = 1 } },
        lualine_x = { "location" },
        lualine_y = {}, lualine_z = {},
      },
      extensions = { "neo-tree", "quickfix", "fugitive" },
    }
  end,
},

  { "lewis6991/gitsigns.nvim", opts = {} },
  { "numToStr/Comment.nvim", opts = {} },

  -- Telescope (search)
  {
    "nvim-telescope/telescope.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    cmd = "Telescope",
    keys = {
      { "<leader>ff", function() require("telescope.builtin").find_files() end, desc = "Find files" },
      { "<leader>fg", function() require("telescope.builtin").live_grep() end,  desc = "Live grep"  },
      { "<leader>fb", function() require("telescope.builtin").buffers() end,    desc = "Buffers"    },
      { "<leader>fh", function() require("telescope.builtin").help_tags() end,  desc = "Help"       },
    },
  },

  -- Treesitter (syntax, folds)
  {
    "nvim-treesitter/nvim-treesitter",
    build = ":TSUpdate",
    opts = {
      ensure_installed = { "lua", "vim", "bash", "python", "json", "yaml", "markdown", "markdown_inline" },
      highlight = { enable = true },
      indent = { enable = true },
    },
    config = function(_, opts) require("nvim-treesitter.configs").setup(opts) end,
  },

  -- Neovim Lua dev ergonomics
  { "folke/neodev.nvim", ft = "lua", opts = {} },

  -- LSP + completion
  { "williamboman/mason.nvim", opts = {} },

  {
    "williamboman/mason-lspconfig.nvim",
    dependencies = { "williamboman/mason.nvim", "neovim/nvim-lspconfig", "hrsh7th/cmp-nvim-lsp" },
    opts = function()
      local lspconfig = require("lspconfig")

      -- Capabilities (gracefully enhanced if cmp is present)
      local capabilities = vim.lsp.protocol.make_client_capabilities()
      local ok, cmp_lsp = pcall(require, "cmp_nvim_lsp")
      if ok then capabilities = cmp_lsp.default_capabilities(capabilities) end

      -- Buffer-local LSP keymaps
      local on_attach = function(_, bufnr)
        local function bmap(mode, lhs, rhs, desc)
          vim.keymap.set(mode, lhs, rhs, { buffer = bufnr, silent = true, desc = desc })
        end
        bmap("n", "gd", vim.lsp.buf.definition, "Goto Definition")
        bmap("n", "gr", vim.lsp.buf.references, "References")
        bmap("n", "K",  vim.lsp.buf.hover,      "Hover")
        bmap("n", "<leader>rn", vim.lsp.buf.rename,      "Rename")
        bmap("n", "<leader>ca", vim.lsp.buf.code_action, "Code Action")
        bmap("n", "<leader>f",  function() vim.lsp.buf.format({ async = true }) end, "Format")
      end

      return {
        ensure_installed = { "bashls", "pyright", "lua_ls", "jsonls", "yamlls", "html" },
        automatic_installation = true,

        -- Portable way: handlers inside setup (no setup_handlers call)
        handlers = {
          function(server)
            lspconfig[server].setup {
              capabilities = capabilities,
              on_attach = on_attach,
            }
          end,
          ["lua_ls"] = function()
            lspconfig.lua_ls.setup {
              capabilities = capabilities,
              on_attach = on_attach,
              settings = {
                Lua = {
                  diagnostics = { globals = { "vim" } },
                  workspace   = { checkThirdParty = false },
                },
              },
            }
          end,
        },
      }
    end,
  },

  { "neovim/nvim-lspconfig" },

  {
    "hrsh7th/nvim-cmp",
    dependencies = {
      "hrsh7th/cmp-nvim-lsp",
      "hrsh7th/cmp-buffer",
      "hrsh7th/cmp-path",
      "L3MON4D3/LuaSnip",
      "saadparwaiz1/cmp_luasnip",
    },
    opts = function()
      local cmp = require("cmp")
      local luasnip = require("luasnip")
      return {
        snippet = { expand = function(args) luasnip.lsp_expand(args.body) end },
        mapping = cmp.mapping.preset.insert({
          ["<C-Space>"] = cmp.mapping.complete(),
          ["<CR>"]      = cmp.mapping.confirm({ select = true }),
          ["<Tab>"]     = cmp.mapping(function(fallback)
            if cmp.visible() then cmp.select_next_item()
            elseif luasnip.expand_or_jumpable() then luasnip.expand_or_jump()
            else fallback() end
          end, { "i", "s" }),
          ["<S-Tab>"]   = cmp.mapping(function(fallback)
            if cmp.visible() then cmp.select_prev_item()
            elseif luasnip.jumpable(-1) then luasnip.jump(-1)
            else fallback() end
          end, { "i", "s" }),
        }),
        sources = cmp.config.sources({
          { name = "nvim_lsp" },
          { name = "luasnip" },
          { name = "path" },
          { name = "buffer" },
        }),
      }
    end,
    config = function(_, opts) require("cmp").setup(opts) end,
  },

  -- Theme: Obsidian-like gray + color
{
  "navarasu/onedark.nvim",
  priority = 1000,
  config = function()
    require("onedark").setup({
      style = "dark",
      diagnostics = { darker = true },
      colors = {
        bg0 = "#1e1e1e", bg1 = "#363636", bg_d = "#262626",
        fg = "#ECECEC", red = "#FF6E6E", green = "#B9F27C",
        yellow = "#FFD76E", blue = "#8CCEFF", purple = "#D4AFFF", cyan = "#7DE1FF",
      },
      highlights = {
        Normal       = { fg = "#ECECEC", bg = "#1e1e1e" },
        NormalNC     = { fg = "#E0E0E0", bg = "#1e1e1e" },
        Comment      = { fg = "#9EA4AA", italic = true },
        String       = { fg = "#C8F6A3" },
        Function     = { fg = "#9BB8FF" },
        Keyword      = { fg = "#FFA870" },
        Type         = { fg = "#9DE6FF" },
        Constant     = { fg = "#FFD0AA" },
        Number       = { fg = "#F3B482" },
        Boolean      = { fg = "#F3B482" },

        LineNr       = { fg = "#5e5e5e", bg = "#1e1e1e" },
        CursorLineNr = { fg = "#DEDEDE", bg = "#363636", bold = true },

        NormalFloat  = { bg = "#363636" },
        FloatBorder  = { bg = "#363636", fg = "#3A3A3A" },
        CursorLine   = { bg = "#363636" },
        Pmenu        = { bg = "#363636", fg = "#E8E8E8" },
        PmenuSel     = { bg = "#2A2A2A", fg = "#FFFFFF", bold = true },
        StatusLine   = { bg = "#363636", fg = "#DADADA" },
        StatusLineNC = { bg = "#1e1e1e", fg = "#A0A0A0" },
        VertSplit    = { fg = "#3A3A3A" },
        WinSeparator = { fg = "#3A3A3A" },

        TabLine      = { bg = "#1e1e1e" },
        TabLineSel   = { bg = "#1e1e1e" },
        TabLineFill  = { bg = "#363636" },

        TelescopeNormal       = { bg = "#1e1e1e" },
        TelescopePromptNormal = { bg = "#363636" },
        TelescopeBorder       = { bg = "#1e1e1e", fg = "#3A3A3A" },

        DiagnosticError = { fg = "#FF7373" },
        DiagnosticWarn  = { fg = "#FFD37A" },
        DiagnosticInfo  = { fg = "#89C7FF" },
        DiagnosticHint  = { fg = "#86F2FF" },

        WhichKey          = { fg = "#ECECEC", bg = "#363636" },
        WhichKeyNormal    = { bg = "#363636" },
        WhichKeyDesc      = { fg = "#E0E0E0", bg = "#363636" },
        WhichKeyGroup     = { fg = "#C0C0C0", bg = "#363636" },
        WhichKeySeparator = { fg = "#808080", bg = "#363636" },
        WhichKeyFloat     = { bg = "#363636" },
        WhichKeyBorder    = { bg = "#363636", fg = "#3A3A3A" },
      },
    })
    require("onedark").load()

    -- Recolor Neo-tree after the theme is loaded (and on future ColorScheme events)
    local function recolor_neotree()
      local hl = vim.api.nvim_set_hl
      -- icons → #ffcb63
      hl(0, "NeoTreeFileIcon",      { fg = "#ffcb63" })
      hl(0, "NeoTreeDirectoryIcon", { fg = "#ffcb63" })
      hl(0, "NeoTreeExpander",      { fg = "#ffcb63" })
      -- title + names → #a0a0a0
      hl(0, "NeoTreeRootName",      { fg = "#a0a0a0", bold = true })
      hl(0, "NeoTreeDirectoryName", { fg = "#a0a0a0" })
      hl(0, "NeoTreeFileName",      { fg = "#a0a0a0" })
      hl(0, "NeoTreeTitleBar",      { fg = "#a0a0a0" })
    end
    recolor_neotree()
    vim.api.nvim_create_autocmd("ColorScheme", { callback = recolor_neotree })
  end,
},

-- File tree (Neo-tree)
{
  "nvim-neo-tree/neo-tree.nvim",
  branch = "v3.x",
  dependencies = { "nvim-lua/plenary.nvim", "nvim-tree/nvim-web-devicons", "MunifTanjim/nui.nvim" },
  cmd = "Neotree",
  keys = {
    { "<leader>ot", "<cmd>Neotree toggle reveal<CR>", desc = "Tree only toggle/reveal" },
  },
  opts = {
    -- stop heavy git jobs → fixes EMFILE storms for huge repos
    enable_git_status = false,

    filesystem = {
      follow_current_file = { enabled = true },
      use_libuv_file_watcher = true,
      filtered_items = {
        hide_dotfiles = false,
        hide_gitignored = false,
        hide_by_name = { ".git", "node_modules", ".cache" },
        never_show    = { ".git" },
        never_show_by_pattern = {
          "all/.config/emacs/.local/straight/.*",
          "%.git/modules/linux/.themes/.*",
        },
      },
    },

    window = {
      width = 32,
      auto_expand_width = false, -- Shift+E will toggle this dynamically
  mappings = {
    -- kill hjkl so they don't fight NEIO
    ["h"] = "none", ["j"] = "none", ["k"] = "none", ["l"] = "none",

    -- NEIO
    ["n"]    = "close_node",
    ["o"]    = "open",
    ["<cr>"] = "open",
    ["e"]    = function(_) vim.cmd("normal! j") end, -- down
    ["i"]    = function(_) vim.cmd("normal! k") end, -- up

    -- info (version-proof)
    ["I"] = function(state)
      local c = state.commands
      local fn = c and (c.show_info_popup or c.show_file_info)
      if fn then fn(state) else vim.notify("Neo-tree: no info action", vim.log.levels.WARN) end
    end,

    -- width toggle + collapse-all
    ["E"] = "toggle_auto_expand_width",
    ["Z"] = "close_all_nodes",
  },
    },
  },
},

-- Tabs-as-buffers (Bufferline)
{
  "akinsho/bufferline.nvim",
  version = "*",
  dependencies = { "nvim-tree/nvim-web-devicons" },
  opts = {
    options = {
      diagnostics = "nvim_lsp",
      separator_style = "thin",
      show_close_icon = false,
      offsets = {
        { filetype = "neo-tree", text = "Explorer", highlight = "Directory", separator = true },
      },
  custom_filter = function(buf, buf_nums)
    -- hide terminal buffers from the tabline
    return vim.bo[buf].buftype ~= "terminal"
  end,
    },
  highlights = {
    -- the bar behind the tabs
    fill = { bg = "#363636" },

    -- default (unselected) tabs
    background = { bg = "#363636", fg = "#A8A8A8" },
    separator = { fg = "#363636", bg = "#363636" },
    separator_visible = { fg = "#363636", bg = "#363636" },
    separator_selected = { fg = "#363636", bg = "#1e1e1e" }, -- clean seam

    -- selected tab
    buffer_selected = { bg = "#1e1e1e", fg = "#ECECEC", bold = true },
    indicator_selected = { fg = "#1e1e1e", bg = "#1e1e1e" },

    -- when the tree is open, the divider to its right
    offset_separator = { fg = "#363636", bg = "#363636" },

    -- close buttons (optional)
    close_button = { bg = "#363636", fg = "#7A7A7A" },
    close_button_selected = { bg = "#1e1e1e", fg = "#E0E0E0" },
  }
  },
},
}

require("lazy").setup(plugins, {
  ui = { border = "rounded" },
  rocks = { enabled = false, hererocks = false }, -- silence luarocks noise
})
