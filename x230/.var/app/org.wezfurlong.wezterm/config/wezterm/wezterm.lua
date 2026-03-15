local wezterm = require 'wezterm'
local config = {}

config.font_locator = 'FontConfig'

local function _norm(s) return (s or ""):lower():gsub("%s+",""):gsub("[%p_%-%/]","") end
local function _strip_nf_variants(n)
  -- Collapse ONLY Nerd Font suffix forms; DO NOT strip 'mono' from real families.
  return n
    :gsub("nerdfontmono$","nerdfont")
    :gsub("nerdfontpropo$","nerdfont")
    :gsub("nerdfont$", "")
end
local ALIASES = {
  sfmononerdfont = "SF Mono",
  sfmononerdfontmono = "SF Mono",
  sanfranciscomono = "SF Mono",
}
local function filter_available_families(candidates)
  local out = {}
  if not (wezterm.gui and wezterm.gui.enumerate_fonts) then return out end
  local have_by_norm, have_by_base, have_norm_list = {}, {}, {}
  for _, f in ipairs(wezterm.gui.enumerate_fonts()) do
    local n = _norm(f.family)
    have_by_norm[n] = f.family
    table.insert(have_norm_list, n)
    local base = _strip_nf_variants(n)
    have_by_base[base] = have_by_base[base] or {}
    table.insert(have_by_base[base], f.family)
  end
  local function pick(name)
    local n = _norm(name)
    -- alias preference first (e.g. prefer 'SF Mono' over NF variants)
    local alias = ALIASES[n]
    if alias and have_by_norm[_norm(alias)] then return have_by_norm[_norm(alias)] end
    -- exact family present?
    if have_by_norm[n] then return have_by_norm[n] end
    -- base match with NF suffixes collapsed
    local base = _strip_nf_variants(n)
    local opts = have_by_base[base]
    if opts and #opts > 0 then
      for _, fam in ipairs(opts) do if _norm(fam):sub(1, #n) == n then return fam end end
      return opts[1]
    end
  end
  for _, name in ipairs(candidates) do
    local fam = pick(name)
    if fam then table.insert(out, fam) end
  end
  return out
end

local b = {
  ["00"]="#1f1f1f",
  ["01"]="#242424",
  ["02"]="#454545",
  ["03"]="#6a6a6a",
  ["04"]="#cbcbcb",
  ["05"]="#d2d4d4",
  ["06"]="#f0f0f0",
  ["07"]="#ffffff",
  ["08"]="#dc322f",
  ["09"]="#cb4b16",
  ["0A"]="#b58900",
  ["0B"]="#4caf50",
  ["0C"]="#15b8cf",
  ["0D"]="#268bd2",
  ["0E"]="#a681d6",
  ["0F"]="#4b6983",
}

local _fonts = {"SFMono Nerd Font"}
local _fonts_filtered = filter_available_families(_fonts)
local function ensured(tbl, fallback) return (tbl and #tbl > 0) and tbl or fallback end
local _term_fonts = ensured(_fonts_filtered, _fonts)
config.font = wezterm.font_with_fallback(_term_fonts)
config.font_size = 11
wezterm.log_info('wezterm.lua fonts → '..table.concat(_term_fonts, ', '))

config.set_environment_variables = config.set_environment_variables or {}
config.set_environment_variables.WEZTERM_FONT = (_term_fonts and _term_fonts[1]) or ''
config.set_environment_variables.WEZTERM_FONT_FALLBACKS = table.concat(_term_fonts or {}, ', ')
config.set_environment_variables.XKB_LOG_LEVEL = '0'
config.window_decorations = 'RESIZE'
local _ui_fonts = {"San Francisco Display"}
do
  local want = _norm((_ui_fonts[1] or ''))
  if want == 'sanfranciscodisplay' or want == 'sanfranciscotext' then
    table.insert(_ui_fonts, 'SF Pro Display')
    table.insert(_ui_fonts, 'SF Pro Text')
  end
end
local _ui_fonts_filtered = filter_available_families(_ui_fonts)
config.window_frame = {
  active_titlebar_bg = b['02'],
  inactive_titlebar_bg = b['02'],
  font_size = 10.5,
}
config.window_frame.font = wezterm.font_with_fallback(ensured(_ui_fonts_filtered, _ui_fonts), { weight = 'Regular' })

config.hide_tab_bar_if_only_one_tab = false
config.use_fancy_tab_bar = true
config.tab_max_width = 32
config.enable_scroll_bar = true
config.adjust_window_size_when_changing_font_size = false
config.scrollback_lines = 10000
config.window_close_confirmation = 'NeverPrompt'
config.skip_close_confirmation_for_processes_named = {
  'bash','sh','zsh','fish','tmux','nu','ssh','nvim','vim'
}
config.window_padding = { left = 4, right = 4, top = 0, bottom = 4 }
config.warn_about_missing_glyphs = false

do
  local _rules_fonts = ensured(_fonts_filtered, _fonts)
  config.font_rules = {
    { intensity = 'Bold',  italic = false, font = wezterm.font_with_fallback(_rules_fonts, { weight = 'Regular' }) },
    { intensity = 'Half',  italic = false, font = wezterm.font_with_fallback(_rules_fonts, { weight = 'Regular' }) },
  }
end

wezterm.on('window-close-requested', function(window, pane)
  window:perform_action(wezterm.action.CloseCurrentWindow { confirm = false }, pane)
end)
wezterm.on('tab-close-requested', function(window, pane)
  window:perform_action(wezterm.action.CloseCurrentTab { confirm = false }, pane)
end)
wezterm.on('pane-close-requested', function(window, pane)
  window:perform_action(wezterm.action.CloseCurrentPane { confirm = false }, pane)
end)

config.colors = {
  foreground = b["05"],
  background = b["01"],
  cursor_bg = b["0A"],
  cursor_fg = b["00"],
  cursor_border = b["0A"],
  selection_bg = "#4b6983",
  selection_fg = "#ffffff",
  scrollbar_thumb = b["0F"],
  split = b["01"],
  ansi = { b["00"], b["08"], b["0B"], b["0A"], b["0D"], b["0F"], b["0C"], b["06"] },
  brights = { b["03"], b["09"], b["01"], b["02"], b["04"], b["0E"], b["05"], b["07"] },
  tab_bar = {
    background = b["02"],
    inactive_tab_edge = b["02"],
    active_tab        = { bg_color = b["01"], fg_color = b["07"], intensity = 'Normal', italic = false },
    inactive_tab      = { bg_color = b["02"], fg_color = b["05"] },
    inactive_tab_hover= { bg_color = b["03"], fg_color = b["06"], italic = true },
    new_tab           = { bg_color = b["02"], fg_color = b["05"] },
    new_tab_hover     = { bg_color = b["02"], fg_color = b["06"] },
  },
}

-- Tab titles: foreground process + index
local function _basename(path)
  return (path or ''):gsub('^.+[/\\]', '')
end
local function _tab_title(tab)
  local pane = tab.active_pane
  local title = ''
  if pane then
    local proc_info = pane:get_foreground_process_info()
    if proc_info and proc_info.name then
      title = _basename(proc_info.name)
    end
    if title == '' then
      local pt = pane:get_title()
      if pt and #pt > 0 then
        title = pt
      end
    end
  end
  if title == '' then
    title = 'tab ' .. tostring(tab.tab_index + 1)
  end
  return title
end
wezterm.on('format-tab-title', function(tab, tabs, panes, cfg, hover, max_width)
  local idx = tab.tab_index + 1
  local is_active = tab.is_active
  local bg = is_active and b['01'] or b['02']
  local fg = is_active and b['07'] or b['05']
  local title = _tab_title(tab)
  return {
    {Background={Color=bg}},
    {Foreground={Color=fg}},
    {Text=(' ' .. idx .. ' ' .. title .. ' ')},
  }
end)

local act = wezterm.action
config.keys = {
  {key='t', mods='CTRL|SHIFT', action=act.SpawnTab('CurrentPaneDomain')},
  {key='[', mods='CTRL|SHIFT', action=act.ActivateTabRelative(-1)},
  {key=']', mods='CTRL|SHIFT', action=act.ActivateTabRelative(1)},
  {key='S', mods='CTRL|SHIFT', action=wezterm.action_callback(function(window, _)
    local o = window:get_config_overrides() or {}
    if o.enable_scroll_bar == nil then o.enable_scroll_bar = true end
    o.enable_scroll_bar = not o.enable_scroll_bar
    window:set_config_overrides(o)
  end)},
}
config.bold_brightens_ansi_colors = false
config.term = 'wezterm'

-- left-stack mux (single, deferred)
local mux = wezterm.mux

local guix_zsh = os.getenv('HOME') .. '/.guix-extra-profiles/core/core/bin/zsh'

-- Build args to spawn a pane that runs cmd then drops to interactive zsh.
-- Uses flatpak-spawn --host when inside the sandbox, direct zsh otherwise.
local function host_pane_args(cmd)
  local script = cmd .. '; exec ' .. guix_zsh .. ' -i'
  if os.getenv('FLATPAK_ID') then
    return { 'flatpak-spawn', '--host', guix_zsh, '-lc', script }
  else
    return { guix_zsh, '-lc', script }
  end
end

wezterm.on('gui-startup', function(cmd)
  if os.getenv('WEZ_LEFT_STACK') ~= '1' then
    mux.spawn_window(cmd or {})
    return
  end

  local vs = math.max(5, math.min(tonumber(os.getenv('VSPLIT') or '70'), 95)) / 100.0
  local hs = math.max(5, math.min(tonumber(os.getenv('HSPLIT') or '48'), 95)) / 100.0

  -- Each pane launches zsh directly with its command — no bash, no echo
  local tab, left, window = mux.spawn_window({
    args = host_pane_args('cd ~/DotCortex && fastfetch'),
  })

  local right = left:split{
    direction = 'Right', size = vs,
    args = host_pane_args('cd ~/DotCortex && swaptop || clear'),
  }

  local bottom = left:split{
    direction = 'Bottom', size = hs,
    args = host_pane_args('swapfetch --watch 5 || printf "swapfetch not found\\n"'),
  }

  -- maximize after layout
  wezterm.time.call_after(0.1, function()
    local gw = window:gui_window()
    if gw and gw.maximize then gw:maximize() end
  end)
end)
return config
