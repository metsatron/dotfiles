;; sanctuary-sx

;; An XFCE desktop stack for the SX-Window / Ko-Window continuation habitat.
;; XFCE is the workshop chassis; all packages come from Guix directly (no source build
;; required). This profile is sourced after =desktop-common= inside the container.


;; [[file:../../../../../guix.org::*sanctuary-sx][sanctuary-sx:1]]
;; Virtual Habitat — sanctuary-sx Guix profile
;; XFCE desktop stack for the SX-Window / Ko-Window continuation habitat.
;; desktop-common is sourced separately by the launcher.
;; Apply: make guix-sanctuary-sx
(specifications->manifest
 '(
   ;; XFCE session, window manager, and configuration subsystem
   "xfce4-session"
   "xfwm4"
   "xfconf"
   ;; Desktop environment components
   "xfce4-panel"
   "xfce4-settings"
   "xfdesktop"
   "xfce4-appfinder"
   ;; File manager
   "thunar"
   "gvfs"        ; GIO volume/trash backends for thunar trash:///
   "tumbler"     ; thumbnail service consumed by thunar
   ;; Terminal emulator
   "xfce4-terminal"
   ;; Garcon — XFCE application/settings menu library; exposes share/desktop-directories/
   ;; needed by xfce4-settings-manager to populate its category grid via Garcon menus.
   "garcon"
   ;; Image viewer
   "ristretto"
   ;; Text editor
   "mousepad"
;; Archive manager
    "engrampa"
    ;; Exo — helper library providing exo-desktop-item-edit for launcher editing
    "exo"
   ;; Session bus (required for dbus-run-session launcher)
   "dbus"
   ;; Flatpak portal services for sanctuary-run Flatpak apps using shared stores.
   "flatpak"
   "xdg-desktop-portal"
   "xdg-desktop-portal-gtk"
   ;; Standard X11 debug and display utilities
   "xterm"       ; fallback terminal
   "xdpyinfo"    ; display info
   "xwininfo"    ; window inspection
   "xrandr"      ; display configuration
   ;; Godzilla XS-86000 runtime spine: shared media library consumers,
   ;; arcade, Wine, MIDI, ROM lab, and Japanese text input/font support.
   "mame"
   "scummvm"
   "wine"
   "winetricks"
   "audacity"
   "audacious"
   "vlc"
   "openjdk"
   "retroarch"
   "dosbox-staging"
   "mt32emu"
   "fluidsynth"
   "qsynth"
   "timidity++"
   "alsa-utils"
   "jack2"
   "qjackctl"
   "imhex"
   "ghex"
   "hexedit"
   "vbindiff"
   "file"
   "xxd"
   "jq"
   "ripgrep"
   "git"
   "make"
   "cmake"
   "ninja"
   "pkg-config"
   "gcc-toolchain"
   "binutils"
   "gdb"
   "python"
   "python-pillow"
   "perl"
   "ruby"
   "imagemagick"
   "gimp"
   "grafx2"
   "mtpaint"
   "ffmpeg"
   "sox"
   "zip"
   "unzip"
   "7zip"
   "xdelta"
   "lhasa"
   "unrar"
   "cabextract"
   "innoextract"
   "xorriso"
   "bchunk"
   "font-google-noto"
   "font-google-noto-sans-cjk"
   "font-ipa"
   "font-ipa-ex"
   "fcitx5"
   ))
;; sanctuary-sx:1 ends here
