#!/bin/zsh
# ~/.zprofile

if [[ -o login ]]; then
  if command -v neofetch >/dev/null 2>&1; then
    neofetch --ascii ~/.local/share/neofetch/CoplandOS.neofetch --ascii_colors 6 4
  fi
fi

