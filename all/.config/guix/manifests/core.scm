;; Guix User profile manifests
;; Tangling target: =all/.config/guix/manifests/core.scm= and friends.

;; [[file:../../../../guix.org::*Guix User profile manifests][Guix User profile manifests:1]]
(specifications->manifest
 '(
   "git" "git-extras"
   "jq" "direnv" "htop" "btop" "ranger"
   "maak" "guile" "chafa"
   "glibc-locales"   ; for UTF-8 locales
   "procps"
   "nss-certs"       ; TLS certs for HTTPS
   "emacs"           ; or "emacs-pgtk" if you prefer pgtk
   "emacs-vterm"     ; native vterm module for Emacs
   "libvterm"
   "emacs-fzf" "fzf" "fzf-tab"
   "emacs-zoxide" "zoxide"
   "neovim"
   "zsh" "zsh-syntax-highlighting" "zsh-completions" "zsh-autopair"
   "zsh-vi-mode" "zsh-autosuggestions" "zsh-history-substring-search"
   "tmux"
   "moreutils"
   "flatpak"
   "fastfetch" "wfetch" "uwufetch" "macchina"
   "rofi"
   ;; "kitty"
   "gimp" "inkscape" "birdtray" "icedove" "gnome-boxes"
   "vlc"
   ;; "audacity"
   "appmenu-gtk-module"
   "cdemu-client" "cdemu-daemon"
   "node"

   "python" "python-pip"
   "python-numpy" "python-sympy" "python-coloredlogs" "python-humanfriendly"
   "python-send2trash" "python-websockets" "python-unidecode" "python-wheel"

   "smem"

   "rust"
   ;; Moved to Cargo:
   ;; "starship"
   ;; "ripgrep"      ; now cargo ripgrep
   ;; "fd"           ; now cargo fd-find
   ;; "bat"          ; now cargo bat
   ;; "lsd"

   ;; Require building
   ;; "gwenview"
   ))
;; Guix User profile manifests:1 ends here
