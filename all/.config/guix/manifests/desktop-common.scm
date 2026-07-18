;; desktop-common

;; Packages shared across all three desktop sanctuaries. Extracted from =core.scm=:
;; host-only items (gimp, inkscape, vlc, gnome-boxes, cdemu, deskflow, flatpak,
;; maak, guile, rofi, alternate fetch tools, borg, inotify-tools, node, smem, Python science
;; stack) stay in =core.scm= only.


;; [[file:../../../../package-guix-habitat.org::*desktop-common][desktop-common:1]]
;; Virtual Habitat — desktop-common Guix profile
;; Packages shared across all desktop sanctuaries.
;; Host-only items (GUIs, package managers, loom tools) remain in core.scm.
;; Apply: guix package -m manifests/desktop-common.scm -p ~/.guix-extra-profiles/desktop-common/desktop-common
;; TODO (Phase 1A): apply once /gnu/store bind-mount is validated in a throwaway Distrobox
(specifications->manifest
 '(
   ;; --- Editors ---
   "emacs"
   "emacs-vterm" "libvterm"
   "emacs-fzf"   "fzf" "fzf-tab"
   "emacs-zoxide" "zoxide"
   "neovim"

   ;; --- Shell ---
   "zsh" "zsh-syntax-highlighting" "zsh-completions" "zsh-autopair"
   "zsh-vi-mode" "zsh-autosuggestions" "zsh-history-substring-search"
   "tmux"

   ;; --- Shell identity and prompt ---
   ;; fastfetch is consumed by the declared shell identities in both the
   ;; Redstone and SX rooms.  Keep it in the shared runtime rather than relying
   ;; on the host core profile leaking into one launcher but not another.
   "fastfetch"
   "starship"

   ;; --- Core utilities ---
   "git" "git-extras"
   "jq" "direnv"
   "htop" "btop" "ranger" "chafa"
   "moreutils"
   "ncurses"   ; clear, tput, reset, tset, infocmp — terminal control on PATH for
               ; every sanctuary shell (was only in room-fvwm95/sanctuary-godzilla-xs, so
               ; `clear` was "command not found" in the IceWM Redstone sanctuary)

   ;; --- Clipboard (host-side bridge for sanctuary X selections) ---
   "xclip"

   ;; --- X cursor theming (Win95 cursors via Chicago95 Xcursor theme) ---
   ;; libX11 dlopens libXcursor.so.1 to render themed cursors when
   ;; XCURSOR_THEME is set. Without this, all X apps fall back to the
   ;; built-in X cursor font (basic black arrows).
   "libxcursor"
   "libxrender"    ; libXcursor runtime dep
   "libxfixes"     ; libXcursor runtime dep

   ;; --- Runtime & certs ---
   "python"
   "gamemode"
   "glibc-locales"
   "nss-certs"
   ))
;; desktop-common:1 ends here
