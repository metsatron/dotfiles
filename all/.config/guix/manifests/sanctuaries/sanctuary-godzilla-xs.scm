;; sanctuary-godzilla-xs

;; An XFCE desktop stack for the SX-Window / Ko-Window continuation habitat.
;; XFCE is the workshop chassis; all packages come from Guix directly (no source build
;; required). This profile is sourced after =desktop-common= inside the container.


;; [[file:../../../../../package-guix-habitat.org::*sanctuary-godzilla-xs][sanctuary-godzilla-xs:1]]
;; Virtual Habitat — sanctuary-godzilla-xs Guix profile
;; XFCE desktop stack for the SX-Window / Ko-Window continuation habitat.
;; desktop-common is sourced separately by the launcher.
;; gvfs is present (GIO volume/trash backends for thunar trash:///) and is
;; now SAFE because the launcher runs sanctuary-trash-shield before starting
;; the desktop. Background: distrobox bind-mounts the host home at /home/<user>
;; AND passes the host root recursively at /run/host, so the host's autofs
;; fleet NFS mounts (~/mnt/x230, ~/mnt/t480, …) surface INSIDE the container's
;; own mount namespace as real mount points via BOTH paths. gvfs's trash
;; aggregator (gvfsd-trash) walks every visible mount point looking for
;; $topdir/.Trash-$uid, so without the shield it merged those remote machines'
;; trash into this sandboxed room's trash:/// (measured historically: 392
;; entries = 68 local + 324 leaked from the host's real ~/mnt/x230/.Trash-1000).
;; sanctuary-trash-shield (see sanctuary-distrobox.org) closes this at launch, inside the
;; container's isolated mount namespace: it makes the two passthrough parents
;; rprivate (so nothing below can propagate to the host) then tmpfs-masks the
;; whole ~/mnt tree via both reachable paths, leaving every fleet mount
;; unreachable (ENOENT). gvfs then finds only the guest-home trash, which is
;; exactly what a sandbox should have. Re-trigger-proof against autofs (masks
;; OVER the mounts, never unmounts them) and future-proof (masks the parent, so
;; a new fleet machine is covered with no change). If you ever run gvfs in a
;; room WITHOUT the shield wired into its launcher, the leak returns — keep the
;; two together. See redstone-9x-state-digest.md.
;; Apply: make guix-sanctuary-godzilla-xs
(use-modules (gnu packages)
             (local packages fbneo-libretro)
             (local packages px68k-libretro)
             (local packages quasi88-libretro)
             (local packages np2kai)
             (local packages tsugaru))

(packages->manifest
 (cons* libretro-px68k
        libretro-fbneo
        libretro-quasi88
        retropie-np2kai
        retropie-tsugaru
        (map specification->package
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
   "gvfs"        ; GIO volume/trash backends for thunar trash:/// — safe behind sanctuary-trash-shield
   "tumbler"     ; thumbnail service consumed by thunar
   ;; MIME/content-type database + icon-theme fallback for GIO content-type and
   ;; GIcon resolution (g_content_type_guess, icon lookups) used by xfdesktop and
   ;; tumbler. Verified absent from this manifest's package closure 2026-07-10
   ;; (guix show on tumbler/gvfs/glib/xfce4-panel/xfdesktop — none declare them;
   ;; Guix's gtk+ does not propagate them). Candidate fix for the 2026-07-07
   ;; GLib-GObject null-instance warnings (session dotcortex/2026-07/07-15-47)
   ;; — confirm via the live SX test checklist before closing that defect.
   "shared-mime-info"
   "desktop-file-utils"
   "hicolor-icon-theme"
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
   ))))
;; sanctuary-godzilla-xs:1 ends here
