;; desktop-common

;; Packages shared across all three desktop sanctuaries. Extracted from =core.scm=:
;; host-only items (gimp, inkscape, vlc, gnome-boxes, cdemu, deskflow, flatpak,
;; maak, guile, rofi, *fetch, borg, inotify-tools, node, smem, Python science
;; stack) stay in =core.scm= only.


;; [[file:../../../../guix.org::*desktop-common][desktop-common:1]]
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

   ;; --- Core utilities ---
   "git" "git-extras"
   "jq" "direnv"
   "htop" "btop" "ranger" "chafa"
   "moreutils"

   ;; --- Runtime & certs ---
   "python"
   "glibc-locales"
   "nss-certs"
   ))
;; desktop-common:1 ends here
