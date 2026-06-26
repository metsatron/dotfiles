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
   ;; Terminal emulator
   "xfce4-terminal"
   ;; Session bus (required for dbus-run-session launcher)
   "dbus"
   ;; Standard X11 debug and display utilities
   "xterm"       ; fallback terminal
   "xdpyinfo"    ; display info
   "xwininfo"    ; window inspection
   "xrandr"      ; display configuration
   ))
;; sanctuary-sx:1 ends here
