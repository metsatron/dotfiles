;; Guix User profile manifests
;; Tangling target: =all/.config/guix/manifests/core.scm= and friends.

;; [[file:../../../../package-guix.org::*Guix User profile manifests][Guix User profile manifests:1]]
(specifications->manifest
 '(
   "git" "git-extras"
   "jq" "direnv" "htop" "btop" "ranger" "unrar" ; Xarchiver RAR backend (RAR 7 compression support)
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
   "croc"            ; encrypted peer-to-peer file transfer
   "flatpak"
   ;; distrobox: DELIBERATELY ABSENT — lives in the nala/system lane (ruling 3c51cfb4d, re-sealed 2026-07-12).
   ;; The Guix build wraps a store-path podman that mis-resolves rootless storage to /var/lib/containers,
   ;; killing every sanctuary launch the moment the profile lands (re-added c894c95ba, detonated by the
   ;; 2026-07-10 fleet apply). The launchers need distrobox ON PATH; /usr/bin/distrobox satisfies that.
   "fastfetch" "wfetch" "uwufetch" "macchina"
   "rofi"
   "clipmenu" "clipnotify" "xsel"   ; rofi clipboard-history mode (Super+z): clipmenud daemon + xsel backend
   "darkman"         ; portal Settings backend for org.freedesktop.appearance color-scheme -- workaround for a xdg-desktop-portal-gtk 1.15.3 bug that always answers color-scheme=0 regardless of dconf state
   ;; "kitty"
   "deskflow"
   "gimp" "inkscape" "birdtray" "icedove" "gnome-boxes"
   "vlc"
   "mpd" "mpd-mpc"   ; music daemon + CLI — fleet DJ lane (music.org: config/autostart; menu.org: rofi-mpd Super+m; library: HelmCortex/NADA)
   ;; whisper-cpp: DELIBERATELY ABSENT — moved to the inference profile with llama-cpp
   ;; (ruling 2026-07-25). It links its own ggml-for-whisper, which carries the identical
   ;; defect: zero AVX2, zero AVX-512, zero FMA, 13108 SSE. Speech-to-text was running
   ;; scalar for as long as this package has been installed.
   ;; "audacity"
   "appmenu-gtk-module"
   ;; "cdemu-client" "cdemu-daemon"  ; removed 2026-07-23 — CLI-only stub: no gcdemu GUI in Guix, no vhba kernel module, daemon never autostarted. Disc-image inspection handled by fuseiso (userspace FUSE mount) instead.
   "fuseiso"          ; userspace FUSE mount for CD/DVD images (.iso/.bin/.nrg/.mdf/.img incl. raw 2352-byte sectors) — browse disc contents in the file manager without root, kernel module, or daemon. Drives the disc-mount-browse Thunar action.
   "node"
   ;; llama-cpp: DELIBERATELY ABSENT — moved to the inference profile (ruling 2026-07-25).
   ;; Guix's stock ggml is compiled for baseline x86_64: disassembly of libggml-cpu.so shows
   ;; zero %ymm (AVX2), zero %zmm (AVX-512) and zero vfmadd against 13158 %xmm — scalar SSE
   ;; on CPUs that advertise avx2+fma, which is most of the reason local embedding ran at
   ;; ~13 tok/s against ~890 tok/s on a properly-built box. The fix needs a per-machine
   ;; -march=native build, so it cannot live in a manifest shared by every machine.
   ;; See "Inference profile" below. Not every machine should carry it either — the X230 is
   ;; the fileserver and does no local inference at all.

   "python"
   "python-numpy" "python-sympy" "python-coloredlogs" "python-humanfriendly"
   "python-send2trash" "python-websockets" "python-unidecode" "python-wheel"
   "python-pillow"   ; ranger's kitty image-preview method imports PIL under ranger's own guix python — not propagated by the ranger package (verified: guix show ranger has no pillow dependency, and testing ranger's actual interpreter with its own GUIX_PYTHONPATH raised ModuleNotFoundError)

   "smem"
   "mandoc"          ; roff→HTML renderer for the fleet documentation library (sanctuary-docs.org)
   "libheif"         ; heif-dec/heif-info — decode iPhone HEIC photos (herdr-web uploads) to JPEG/PNG for agent vision; agents' ffmpeg tile-grid fallback lives in the heic-photos userspace skill

   ;; rust/cargo managed via dotcortex-rust-env (rustup) — not Guix
   ;; cargo crates managed via package-cargo.org
   ;; "starship"
   ;; "ripgrep"      ; now cargo ripgrep
   ;; "fd"           ; now cargo fd-find
   ;; "bat"          ; now cargo bat
   ;; "lsd"

   ;; Require building
   ;; "gwenview"
   ))
;; Guix User profile manifests:1 ends here
