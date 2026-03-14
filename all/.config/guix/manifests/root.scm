;; [[file:../../../../guix.org::*Guix User profile manifests][Guix User profile manifests:3]]
(specifications->manifest
 '(
   "git" "htop" "jq" "direnv" "btop"
   "maak" "guile"
   "python" "node"
   "glibc-locales"   ; for UTF-8 locales
   "nss-certs"       ; TLS certs for HTTPS
   "neovim"
   "lsd" "ranger"
   "fzf" "emacs-fzf" "fzf-tab"
   "zsh" "zsh-syntax-highlighting" "zsh-completions" "zsh-autopair"
   "zsh-vi-mode" "zsh-autosuggestions" "zsh-history-substring-search"
   "python-numpy" "python-sympy" "python-coloredlogs" "python-humanfriendly"
   "python-send2trash" "python-websockets" "python-unidecode" "python-wheel"
   "moreutils"
   "flatpak"
   ;; "cdemu-client" "cdemu-daemon"

   "cargo"
   ;; Removed here, migrated to Cargo:
   ;; "ripgrep"
   ;; "fd"
   ;; "bat"
   ))
;; Guix User profile manifests:3 ends here
