#!/bin/zsh
#!/bin/zsh
# My .zshrc
# Metsatron <metsratron@posteo.net>
# https://github.com/metsarono/dotfiles/blob/master/.zshrc
# ~/.zshrc
# Load modular Zsh config from ~/.dotfiles/all
neofetch --ascii ~/.local/share/neofetch/CoplandOS.neofetch --ascii_colors 6 4

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

for file in $HOME/.dotfiles/all/.zsh_*; do
  [ -f "$file" ] && source "$file"
done

# Auto update zplug plugins monthly
zplug check || zplug install
[[ -z "$(zplug check | grep 'out-of-date')" ]] || zplug update

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

