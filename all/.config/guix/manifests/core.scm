;; User profile manifests
;; Tangling target: =all/.config/guix/manifests/dev.scm= and friends.


;; [[file:../../../../guix.org::*User profile manifests][User profile manifests:1]]
(specifications->manifest
 '(
   "git" "htop" "ripgrep" "fd" "jq" "direnv" "btop"
   "python" "node"
   "glibc-locales"   ; for UTF-8 locales
   "nss-certs"       ; TLS certs for HTTPS
   "emacs"           ; or "emacs-pgtk" if you prefer pgtk
   "emacs-vterm"     ; native vterm module for Emacs
   "libvterm"
   "neovim"
   "lsd" "ranger"
   "python-numpy" "python-sympy" "python-coloredlogs" "python-humanfriendly" "python-send2trash" "python-websockets" "python-unidecode" "python-wheel"
   "moreutils"
   "gimp" "inkscape"
   "appmenu-gtk-module"
   ))
;; User profile manifests:1 ends here
