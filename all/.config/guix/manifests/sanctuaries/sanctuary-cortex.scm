;; Virtual Habitat — sanctuary-cortex Guix profile
;; Apply with sanctuary-cortex-guix-apply.
(use-modules (gnu packages)
             (gnu packages gettext)
             (gnu packages gtk)
             (gnu packages xfce)
             (guix gexp)
             (guix packages)
             (guix utils))

;; Guix's stock appmenu-gtk-module build sees GTK and libwnck, but not the
;; XFCE development interfaces, so its auto-detection omits the XFCE panel
;; applet. Build the same pinned source with both integrations enabled and
;; keep the panel descriptor, module, and registrar in the sanctuary profile.
(define appmenu-gtk-module-xfce
  (package
    (inherit appmenu-gtk-module)
    (name "appmenu-gtk-module-xfce")
    (arguments
     (substitute-keyword-arguments (package-arguments appmenu-gtk-module)
       ((#:configure-flags flags #~'())
        #~(cons* "-Dxfce=enabled"
                 "-Dappmenu-gtk-module=enabled"
                 "-Dappmenu-gtk-module:gtk=3"
                 #$flags))
       ((#:phases phases)
        #~(modify-phases #$phases
            ;; The pinned 0.7.6 checkout lists nb twice in po/LINGUAS;
            ;; Meson rejects the resulting duplicate .mo target.
            (add-after 'unpack 'deduplicate-linguas
              (lambda _
                (substitute* "po/LINGUAS"
                  ((" nn nb nr ") " nn nr "))))
            ;; Upstream uses the consuming panel's prefix/libdir, which is an
            ;; immutable input store path in Guix. Keep the plugin and its
            ;; descriptor inside this profile instead.
            (add-after 'deduplicate-linguas 'use-profile-install-paths
              (lambda _
                (substitute*
                    '("applets/meson.build" "data/meson.build")
                  (("xp.get_pkgconfig_variable\\('libdir'\\)")
                   "join_paths(prefix, get_option('libdir'))")
                  (("xp.get_pkgconfig_variable\\('prefix'\\)")
                   "prefix"))))
            ;; The private Cortex boot helper resolves the registrar through
            ;; PATH. The upstream install keeps it in libexec, so expose a
            ;; profile-local command without moving the real service binary.
            (add-after 'install 'expose-registrar-command
              (lambda* (#:key outputs #:allow-other-keys)
                (let ((out (assoc-ref outputs "out")))
                  (mkdir-p (string-append out "/bin"))
                  (symlink
                   (string-append out "/libexec/vala-panel/appmenu-registrar")
                   (string-append out "/bin/appmenu-registrar")))))
            (replace 'fix-install-gtk-module
              (lambda* (#:key outputs #:allow-other-keys)
                (let ((out (assoc-ref outputs "out")))
                  (substitute*
                      "subprojects/appmenu-gtk-module/src/gtk-3.0/meson.build"
                    (("gtk3.get_pkgconfig_variable\\('libdir'\\)")
                     (string-append "'" out "/lib'"))))))))))
    (inputs
     (modify-inputs (package-inputs appmenu-gtk-module)
       (append libxfce4ui xfce4-panel xfconf)))
    (native-inputs
     (modify-inputs (package-native-inputs appmenu-gtk-module)
       (append gettext-minimal)))))

(packages->manifest
 (cons* appmenu-gtk-module-xfce
        (list (specification->package "transmission") "gui")
        (map specification->package
             '(
   ;; XFCE session, window manager, panels, and settings
   "xfce4-session"
   "xfwm4"
   "xfconf"
   "xfce4-panel"
   "xfce4-settings"
   "xfdesktop"
   "xfce4-appfinder"
   "xfce4-notifyd"
   "xfce4-power-manager"
   "xfce4-taskmanager"
   "xfce4-terminal"
   "xfce4-clipman-plugin"
   "xfce4-pulseaudio-plugin"
   "xfce4-whiskermenu-plugin"
   "xfce4-xkb-plugin"
   "xfce4-places-plugin"
   ;; XFCE desktop libraries, menus, file manager, and thumbnails
   "exo"
   "garcon"
   "thunar"
   "thunar-volman"
   "gvfs"
   "tumbler"
   "shared-mime-info"
   "desktop-file-utils"
   "hicolor-icon-theme"
   ;; Session and application bridge
   "dbus"
   "flatpak"
   "xdg-desktop-portal"
   "xdg-desktop-portal-gtk"
   ;; Basic tools used by the projected X230 configuration
   "bash"
   "zsh"
   "coreutils"
   "findutils"
   "grep"
   "sed"
   "gawk"
   "rsync"
   "git"
   "jq"
   ;; Verified Guix equivalents for the shared Nala/apt CLI surface.  The
   ;; host-only Nala executable itself stays outside the guest; these are the
   ;; portable tools that the X230 shell expects to find in Cortex.
   "curl"
   "wget"
   "make"
   "python"
   "tree"
   "htop"
   "btop"
   "ranger"
   "chafa"
   "moreutils"
   "ncurses"
   "lsof"
   "less"
   "which"
   "procps"
   "unzip"
   "zip"
   "openssh"
   "xclip"
   ;; Guest-native replacements for host cargo binaries.  The host builds
   ;; request /lib64/ld-linux-x86-64.so.2, which is not present in Distrobox.
   "ripgrep"
   "fd"
   "bat"
   "eza"
   ;; Keep the channel-pinned Guix CLI available inside Cortex terminals.
   "guix"
   "xdpyinfo"
   "xrandr"
   "xterm"
   ;; --- XFCE panel plugins (X230 catalogue) ---
   ;; docklike and windowck are not packaged in Guix.
   "xfce4-cpugraph-plugin"
   "xfce4-systemload-plugin"
   "xfce4-verve-plugin"
   "xfce4-weather-plugin"
   ;; --- Audio / Media ---
   "pavucontrol"
   "ffmpeg"
   "vlc"
   "audacity"
   "sox"
   "flac"
   "shntool"
   "cuetools"
   ;; --- Desktop applications (Guix equivalents of the nala desktop lane) ---
   ;; transmission is handled above via (list pkg "gui") — GTK4 in Guix,
   ;; no Qt build available.  GTK4 apps cannot export to the global menu.
   "pluma"
   "mate-calc"
   "mate-utils"
   "gthumb"
   "meld"
   "grsync"
   "seahorse"
   "yad"
   "zenity"
   ;; Phone/desktop integration.  The daemon is activated on Cortex's private
   ;; XFCE D-Bus session; its identity and pairing state therefore remain in
   ;; the sanctuary guest home rather than leaking into the host session.
   "kdeconnect"
   ;; --- CLI tools (X230 nala surface) ---
   "mc"
   "vim"
   "screen"
   "trash-cli"
   "xdotool"
   "xmlstarlet"
   "dialog"
   "lynx"
   "plocate"
   "wmctrl"
   ;; --- Fonts ---
   "font-nerd-symbols"
   "font-nerd-fira-code"
   "font-nerd-jetbrains-mono"
   "font-google-noto-emoji"
   "font-dejavu"
   ))))
