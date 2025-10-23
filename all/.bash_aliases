#!/bin/bash
# ~/.bash_aliases
# --------------------------------------------------
# Mètsàtron's Aliases
# --------------------------------------------------

# Add more here
alias pip='/usr/bin/pip'

# Dircolors and color aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# More ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias lh="ls -lh"
alias l='ls -CF'
alias lash="ls -lAsh"
alias sl="ls"

# Alert alias
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Common Useful Aliases
alias g='git status'
alias gss='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gr='git rm'
alias clone='git clone'
alias ..='cd ..'
alias ...='cd ../..'
alias update='sudo apt update && sudo apt upgrade'
alias rm='rm -iv'
alias diff="diff -u"
alias python="python3"
alias mkhttp="python3 -m http.server"
alias json="python3 -m json.tool"
alias perms="stat -c '%A %a %n'"
alias neofetch="neofetch --ascii ~/.local/share/neofetch/CoplandOS.neofetch --colors 15 1 1 1 1 15 --ascii_colors 15 5 1"
alias cpufetch='cpufetch --color "intel" --logo-short --logo-intel-old'
alias heartfetch='brrtfetch $HOME/Pictures/brrtfetch/gifs/random/heart.gif'
alias penguinfetch='brrtfetch $HOME/Pictures/brrtfetch/gifs/random/penguin-yoshi.gif'
alias mariofetch='brrtfetch $HOME/Pictures/brrtfetch/gifs/random/mario.gif'
alias tobifetch='brrtfetch $HOME/Pictures/brrtfetch/gifs/random/toby-fox.gif'
alias v='nvim'
alias vi='nvim'
alias vim='nvim'
alias cd='z'
alias ls='lsd'
alias find='command find'
alias grep='command grep'
alias ff='fd'                  # clean "fd"
alias ffa='fd -H -I'           # include hidden AND ignore .gitignore (broad sweep)
alias ff0='fd -0'              # fd with NUL output
alias rga='rg -n --color=auto'         # nice default for humans
alias rgi='rg -n --color=auto -i'      # case-insensitive default
alias rg0='rg -0 -n --color=never -l'  # NUL-delimited file list (for piping)
alias bat='bat --theme "Solarized (dark)" --style full'
alias cat='bat --theme "Solarized (dark)" --style plain --paging=never'
alias flatseal='flatpak run com.github.tchx84.Flatseal'
alias zen='flatpak run app.zen_browser.zen'
alias discord='flatpak run com.discordapp.Discord'
alias czkawka='flatpak run com.github.qarmin.czkawka'
alias gwe='flatpak run com.leinardi.gwe'
alias logseq='flatpak run com.logseq.Logseq'
alias rustdesk='flatpak run com.rustdesk.RustDesk'
alias codium='flatpak run com.vscodium.codium'
alias newelle='flatpak run io.github.qwersyk.Newelle'
alias ungoogled_chromium='flatpak run io.github.ungoogled_software.ungoogled_chromium'
alias webcamoid='flatpak run io.github.webcamoid.Webcamoid'
alias obsidian='flatpak run md.obsidian.Obsidian'
alias pupgui2='flatpak run net.davidotek.pupgui2'
alias floorp_fp='flatpak run one.ablaze.floorp'
alias freac='flatpak run org.freac.freac'
alias jdownloader='flatpak run org.jdownloader.JDownloader'
alias keepassxc_fp='flatpak run org.keepassxc.KeePassXC'
alias telegram='flatpak run org.telegram.desktop'
alias upscayl='flatpak run org.upscayl.Upscayl'
alias zoom='flatpak run us.zoom.Zoom'
alias clapgrep='flatpak run de.leopoldluley.Clapgrep'
alias bella='flatpak run io.github.josephmawa.Bella'
alias zotero='flatpak run org.zotero.Zotero'
alias xmind='flatpak run net.xmind.XMind'
alias flacon='flatpak run com.github.Flacon'
alias firedragon='flatpak run org.garudalinux.firedragon'
alias rustdesk='flatpak run com.rustdesk.RustDesk'
alias warehouse='flatpak run io.github.flattool.Warehouse'
alias marktext='flatpak run com.github.marktext.marktext'
alias remembrance='flatpak run io.github.dgsasha.Remembrance'
alias picard='flatpak run org.musicbrainz.Picard'
alias mgba='flatpak run io.mgba.mGBA'
alias wezterm='flatpak run org.wezfurlong.wezterm'
alias pied_fp='flatpak run com.mikeasoft.pied'
alias signal-desktop='exec host-wrap /usr/bin/signal-desktop --password-store="gnome-libsecret" "$@"'

# ffetch: fastfetch with WezTerm overlay when inside WezTerm
ffetch() {
  if [[ -n ${WEZTERM_EXECUTABLE-}${WEZTERM_VERSION-} ]]; then
    command fastfetch --config "$HOME/.config/fastfetch/wezterm.jsonc" "$@"
  else
    command fastfetch "$@"
  fi
}
