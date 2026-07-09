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
   "borg"            ; helmcortex-borg multi-endpoint backup
   "inotify-tools"   ; helmcortex-borg watch verb (inotifywait)
   "flatpak"
   "distrobox"             ; Virtual Habitat control plane — sanctuary-exec and launchers require it
   "fastfetch" "wfetch" "uwufetch" "macchina"
   "rofi"
   "clipmenu" "clipnotify" "xsel"   ; rofi clipboard-history mode (Super+z): clipmenud daemon + xsel backend
   "darkman"         ; portal Settings backend for org.freedesktop.appearance color-scheme -- workaround for a xdg-desktop-portal-gtk 1.15.3 bug that always answers color-scheme=0 regardless of dconf state
   ;; "kitty"
   "deskflow"
   "gimp" "inkscape" "birdtray" "icedove" "gnome-boxes"
   "vlc"
   "whisper-cpp"     ; CPU speech-to-text (whisper-transcribe, telegram voice pipeline)
   ;; "audacity"
   "appmenu-gtk-module"
   "cdemu-client" "cdemu-daemon"
   "node"
   "llama-cpp"

   "python"
   "python-numpy" "python-sympy" "python-coloredlogs" "python-humanfriendly"
   "python-send2trash" "python-websockets" "python-unidecode" "python-wheel"
   "python-pillow"   ; ranger's kitty image-preview method imports PIL under ranger's own guix python — not propagated by the ranger package (verified: guix show ranger has no pillow dependency, and testing ranger's actual interpreter with its own GUIX_PYTHONPATH raised ModuleNotFoundError)

   "smem"

   ;; rust/cargo managed via dotcortex-rust-env (rustup) — not Guix
   ;; cargo crates managed via cargo.org
   ;; "starship"
   ;; "ripgrep"      ; now cargo ripgrep
   ;; "fd"           ; now cargo fd-find
   ;; "bat"          ; now cargo bat
   ;; "lsd"

   ;; Require building
   ;; "gwenview"
   ))
;; Guix User profile manifests:1 ends here
