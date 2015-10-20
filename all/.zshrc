#!/bin/zsh
# My .zshrc
# Jerome Leclanche <jerome@leclan.ch>
# https://github.com/jleclanche/dotfiles/blob/master/.zshrc

##
# Somebody set us up the prompt
#

# Let's have some colors first
autoload -U colors && colors

#if [[ -e /usr/share/zsh/site-contrib/powerline.zsh ]]; then
#	# Powerline support is enabled if available, otherwise use a regular PS1
#	. /usr/share/zsh/site-contrib/powerline.zsh
#	VIRTUAL_ENV_DISABLE_PROMPT=true
#elif [[ -e $HOME/.local/lib/python2.7/site-packages/powerline/bindings/zsh/powerline.zsh ]]; then
    #statements
#    . $HOME/.local/lib/python2.7/site-packages/powerline/bindings/zsh/powerline.zsh
#    VIRTUAL_ENV_DISABLE_PROMPT=true
#else
	# Default colors:
	# Cyan for users, red for root, magenta for system users
	local _time="%{$fg[yellow]%}[%*]"
	local _path="%B%{$fg[green]%}%(8~|...|)%7~"
	local _usercol
	if [[ $EUID -lt 1000 ]]; then
		# red for root, magenta for system users
		_usercol="%(!.%{$fg[red]%}.%{$fg[magenta]%})"
	else
		_usercol="$fg[cyan]"
	fi
	local _user="%{$_usercol%}%n@%M"
	local _prompt="%{$fg[white]%}${(r:$SHLVL*2::%#:)}"

	PROMPT="$_time $_user $_path $_prompt%b%f%k "

	RPROMPT='${vcs_info_msg_0_}' # git branch
	if [[ ! -z "$SSH_CLIENT" ]]; then
		RPROMPT="$RPROMPT ⇄" # ssh icon
	fi
#fi

##
# Environment variables
#

# basedir defaults, in case they're not already set up.
# http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
if [[ -z $XDG_DATA_HOME ]]; then
	export XDG_DATA_HOME=$HOME/.local/share
fi

if [[ -z $XDG_CONFIG_HOME ]]; then
	export XDG_CONFIG_HOME=$HOME/.config
fi

if [[ -z $XDG_CACHE_HOME ]]; then
	export XDG_CACHE_HOME=$HOME/.cache
fi

if [[ -z $XDG_DATA_DIRS ]]; then
	export XDG_DATA_DIRS=/usr/local/share:/usr/share
fi

if [[ -z $XDG_CONFIG_DIRS ]]; then
	export XDG_CONFIG_DIRS=/etc/xdg
else
	export XDG_CONFIG_DIRS=/etc/xdg:$XDG_CONFIG_DIRS
fi

# add ~/bin to $PATH
path=(~/bin $path)
# add ~/.config/zsh/completion to completion paths
# NOTE: this needs to be a directory with 0755 permissions, otherwise you will
# get "insecure" warnings on shell load!
fpath=($XDG_CONFIG_HOME/zsh/completion $fpath)


##
# zsh configuration
#

# Keep 1000 lines of history within the shell and save it to ~/.cache/shell_history
HISTSIZE=100000
SAVEHIST=100000
HISTFILE=$XDG_CACHE_HOME/shell_history

# shell options
setopt autocd # assume "cd" when a command is a directory
setopt histignorealldups # Substitute commands in the prompt
setopt sharehistory # Share the same history between all shells
setopt promptsubst # required for git plugin
# setopt extendedglob
# Extended glob syntax, eg ^ to negate, <x-y> for range, (foo|bar) etc.
# Backwards-incompatible with bash, so disabled by default.

# Colors!

# 256 color mode
export TERM="xterm-256color"

# Color aliases
if command -V dircolors >/dev/null 2>&1; then
	eval "$(dircolors -b)"
	# Only alias ls colors if dircolors is installed
	alias ls="ls -F --color=auto"
	alias dir="dir --color=auto"
	alias vdir="vdir --color=auto"
fi

alias grep="grep --color=auto"
alias fgrep="fgrep --color=auto"
alias egrep="egrep --color=auto"
alias dmesg="dmesg --color=auto"
# make less accept color codes and re-output them
alias less="less -R"


##
# Completion system
#

autoload -Uz compinit
compinit

zstyle ":completion:*" auto-description "specify: %d"
zstyle ":completion:*" completer _expand _complete _correct _approximate
zstyle ":completion:*" format "Completing %d"
zstyle ":completion:*" group-name ""
zstyle ":completion:*" menu select=2
zstyle ":completion:*:default" list-colors ${(s.:.)LS_COLORS}
zstyle ":completion:*" list-colors ""
zstyle ":completion:*" list-prompt %SAt %p: Hit TAB for more, or the character to insert%s
zstyle ":completion:*" matcher-list "" "m:{a-z}={A-Z}" "m:{a-zA-Z}={A-Za-z}" "r:|[._-]=* r:|=* l:|=*"
zstyle ":completion:*" menu select=long
zstyle ":completion:*" select-prompt %SScrolling active: current selection at %p%s
zstyle ":completion:*" use-compctl false
zstyle ":completion:*" verbose true

zstyle ":completion:*:*:kill:*:processes" list-colors "=(#b) #([0-9]#)*=0=01;31"
zstyle ":completion:*:kill:*" command "ps -u $USER -o pid,%cpu,tty,cputime,cmd"


##
# Keybinds
#

# Use emacs-style keybindings
bindkey -v

bindkey "$terminfo[khome]" beginning-of-line # Home
bindkey "$terminfo[kend]" end-of-line # End
bindkey "$terminfo[kich1]" overwrite-mode # Insert
bindkey "$terminfo[kdch1]" delete-char # Delete
bindkey "$terminfo[kcuu1]" up-line-or-history # Up
bindkey "$terminfo[kcud1]" down-line-or-history # Down
bindkey "$terminfo[kcub1]" backward-char # Left
bindkey "$terminfo[kcuf1]" forward-char # Right
# bindkey "$terminfo[kpp]" # PageUp
# bindkey "$terminfo[knp]" # PageDown

# Bind ctrl-left / ctrl-right
bindkey "\e[1;5D" backward-word
bindkey "\e[1;5C" forward-word

# Bind ctrl-backspace to delete word.
# NOTE: This may not work properly in some emulators
# bindkey "^?" backward-delete-word

# Bind shift-tab to backwards-menu
# NOTE this won't work on Konsole if the new tab button is shown
bindkey "\e[Z" reverse-menu-complete

# Make ctrl-e edit the current command line
autoload edit-command-line
zle -N edit-command-line
bindkey "^e" edit-command-line

# Make sure the terminal is in application mode, when zle is
# active. Only then are the values from $terminfo valid.
if (( ${+terminfo[smkx]} )) && (( ${+terminfo[rmkx]} )); then
	function zle-line-init {
		printf "%s" ${terminfo[smkx]}
	}
	function zle-line-finish {
		printf "%s" ${terminfo[rmkx]}
	}
	zle -N zle-line-init
	zle -N zle-line-finish
fi

# typing ... expands to ../.., .... to ../../.., etc.
rationalise-dot() {
	if [[ $LBUFFER = *.. ]]; then
		LBUFFER+=/..
	else
		LBUFFER+=.
	fi
}
zle -N rationalise-dot
bindkey . rationalise-dot
bindkey -M isearch . self-insert # history search fix


##
# Aliases
#

# some more ls aliases
alias l="ls -CF"
alias ll="ls -l"
alias la="ls -A"
alias lh="ls -lh"
alias lash="ls -lAsh"
alias sl="ls"

# Make unified diff syntax the default
alias diff="diff -u"

# simple webserver
alias mkhttp="python -m http.server"

# json prettify
alias json="python -m json.tool"

# Alias make to a proper amount of cores
# alias make="make -j$(nproc)"

# octal+text permissions for files
alias perms="stat -c '%A %a %n'"

# expand sudo aliases
alias sudo="sudo "


##
# Functions
#

# make a backup of a file
# https://github.com/grml/grml-etc-core/blob/master/etc/zsh/zshrc
bk() {
	cp -a "$1" "${1}_$(date --iso-8601=seconds)"
}

# display a list of supported colors
function lscolors {
	((cols = $COLUMNS - 4))
	s=$(printf %${cols}s)
	for i in {000..$(tput colors)}; do
		echo -e $i $(tput setaf $i; tput setab $i)${s// /=}$(tput op);
	done
}

# get the content type of an http resource
function htmime {
	if [[ -z $1 ]]; then
		print "USAGE: htmime <URL>"
		return 1
	fi
	mime=$(curl -sIX HEAD $1 | sed -nr "s/Content-Type: (.+)/\1/p")
	print $mime
}

# open a web browser on google for a query
function google {
	xdg-open "https://www.google.com/search?q=`urlencode "${(j: :)@}"`"
}

# print a separator banner, as wide as the terminal
function hr {
	print ${(l:COLUMNS::=:)}
}

# launch an app
function launch {
	type $1 >/dev/null || { print "$1 not found" && return 1 }
	$@ &>/dev/null &|
}
alias launch="launch " # expand aliases

# urlencode text
function urlencode {
	print "${${(j: :)@}//(#b)(?)/%$[[##16]##${match[1]}]}"
}

# get public ip
function myip {
	local api
	case "$1" in
		"-4")
			api="http://v4.ipv6-test.com/api/myip.php"
			;;
		"-6")
			api="http://v6.ipv6-test.com/api/myip.php"
			;;
		*)
			api="http://ipv6-test.com/api/myip.php"
			;;
	esac
	curl -s "$api"
	echo # Newline.
}

# Create short urls via http://goo.gl using curl(1).
# Contributed back to grml zshrc
# API reference: https://code.google.com/apis/urlshortener/
function zurl {
	if [[ -z $1 ]]; then
		print "USAGE: $0 <URL>"
		return 1
	fi

	local url=$1
	local api="https://www.googleapis.com/urlshortener/v1/url"
	local data

	# Prepend "http://" to given URL where necessary for later output.
	if [[ $url != http(s|)://* ]]; then
		url="http://$url"
	fi
	local json="{\"longUrl\": \"$url\"}"

	data=$(curl --silent -H "Content-Type: application/json" -d $json $api)
	# Match against a regex and print it
	if [[ $data =~ '"id": "(http://goo.gl/[[:alnum:]]+)"' ]]; then
		print $match
	fi
}


##
# Extras
#

# Git plugin
autoload -Uz vcs_info
zstyle ":vcs_info:*" enable git
zstyle ":vcs_info:(git*):*" get-revision true
zstyle ":vcs_info:(git*):*" check-for-changes true

local _branch="%c%u%m %{$fg[green]%}%b%{$reset_color%}"
local _repo="%{$fg[green]%}%r %{$fg[yellow]%}%{$reset_color%}"
local _revision="%{$fg[yellow]%}%.7i%{$reset_color%}"
local _action="%{$fg[red]%}%a%{$reset_color%}"
zstyle ":vcs_info:*" stagedstr "%{$fg[yellow]%}✓%{$reset_color%}"
zstyle ":vcs_info:*" unstagedstr "%{$fg[red]%}✗%{$reset_color%}"
zstyle ":vcs_info:git*" formats "$_branch:$_revision - $_repo"
zstyle ":vcs_info:git*" actionformats "$_branch:$_revision:$_action - $_repo"
zstyle ':vcs_info:git*+set-message:*' hooks git-stash
# Uncomment to enable vcs_info debug mode
# zstyle ':vcs_info:*+*:*' debug true

function +vi-git-stash() {
	if [[ -s "${hook_com[base]}/.git/refs/stash" ]]; then
		hook_com[misc]="%{$fg_bold[grey]%}~%{$reset_color%}"
	fi
}

precmd() {
	vcs_info
}

# virtualenvwrapper support
# Remember to set $PROJECT_HOME in your profile file!
if command -V virtualenvwrapper_lazy.sh >/dev/null 2>&1; then
	export WORKON_HOME="$XDG_DATA_HOME/virtualenvs"
	source virtualenvwrapper_lazy.sh
	# Arch linux uses python3 by default, this is required to make python2-compatible projects
	alias mkproject2="mkproject -p /usr/bin/python2"
	alias mkvirtualenv2="mkvirtualenv -p /usr/bin/python2"
fi

# User profile
if [[ -e $XDG_CONFIG_HOME/zsh/profile ]]; then
	source $XDG_CONFIG_HOME/zsh/profile
fi

# Check if $LANG is badly set as it causes issues
if [[ $LANG == "C"  || $LANG == "" ]]; then
	>&2 echo "$fg[red]The \$LANG variable is not set. This can cause a lot of problems.$reset_color"
fi

# Syntax highlighting plugin
#if [[ -e /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]]; then
#	source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
#fi

#if [[ -e /usr/share/zsh/plugins/zsh-history-substring-search/zsh-history-substring-search.zsh ]]; then
#	source /usr/share/zsh/plugins/zsh-history-substring-search/zsh-history-substring-search.zsh
#fi

# bind UP and DOWN arrow keys
#zmodload zsh/terminfo
#bindkey "$terminfo[kcuu1]" history-substring-search-up
#bindkey "$terminfo[kcud1]" history-substring-search-down

# # bind P and N for EMACS mode
#bindkey -M emacs '^P' history-substring-search-up
#bindkey -M emacs '^N' history-substring-search-down

# # bind k and j for VI mode
#bindkey -M vicmd 'k' history-substring-search-up
#bindkey -M vicmd 'j' history-substring-search-down

# load zgen
source "$HOME/.config/zsh/zgen/zgen.zsh"

# check if there's no init script
if ! zgen saved; then
    echo "Creating a zgen save"

    zgen oh-my-zsh

    # plugins
    zgen oh-my-zsh plugins/git
    zgen oh-my-zsh plugins/sudo
    zgen oh-my-zsh plugins/command-not-found
    zgen load maverick2000/zsh2000 zsh2000
    zgen load thvitt/tvline tvline
    zgen load zsh-users/zsh-syntax-highlighting
    zgen load tarruda/zsh-autosuggestions

    # bulk load
    zgen loadall <<EOPLUGINS
        zsh-users/zsh-history-substring-search

EOPLUGINS
    # ^ can't indent this EOPLUGINS

    # completions
    zgen load zsh-users/zsh-completions src

    # theme
    zgen oh-my-zsh themes/tvline

    # save all to init script
    zgen save
fi


# Enable autosuggestions automatically
zle-line-init() {
    zle autosuggest-start
}

zle -N zle-line-init

# use ctrl+t to toggle autosuggestions(hopefully this wont be needed as
# zsh-autosuggestions is designed to be unobtrusive)
bindkey '^T' autosuggest-toggle

export KEYTIMEOUT=1

export EDITOR=/usr/bin/vim
export VISUAL=/usr/bin/vim

# if [ "$TMUX" = "" ]; then tmux; fi

if [ -e /usr/lib/python2.7/site-packages/powerline/bindings/tmux/powerline.conf ]; then
      tmux source "/usr/lib/python2.7/site-packages/powerline/bindings/tmux/powerline.conf"

elif [ -e /usr/local/lib/python2.7/site-packages/powerline/bindings/tmux/powerline.conf ]; then
      tmux source "/usr/local/lib/python2.7/site-packages/powerline/bindings/tmux/powerline.conf"
fi
export PATH="/usr/local/sbin:$PATH"
