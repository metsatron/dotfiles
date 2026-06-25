;; room-gaming

;; Shared profile for gaming-wing sanctuaries.  Confirmed Guix packages:
;; - =icewm=, =pcmanfm=, =dbus=, =xterm= — desktop stack (first slice)
;; - =wine64= — WoW64 Wine (runs 32- and 64-bit Windows apps); =winetricks= — helper scripts
;; - Not in Guix or nonguix: =lutris= (→ Flatpak =net.lutris.Lutris= on host), =powershell=


;; [[file:../../../../../guix.org::*room-gaming][room-gaming:1]]
;; Virtual Habitat — room-gaming Guix profile
;; Shared across gaming-wing sanctuaries (redstone-9x, lunestone-b2, commodore, retropie).
;; desktop-common is sourced separately by each launcher.
;; Apply: make guix-room-gaming   OR   loom guix:sanctuary-apply
(specifications->manifest
 '(
   "icewm"       ; Win9x/XP-era WM — Windows-95 theme
   "pcmanfm"     ; GTK file manager (needs dbus session)
   "dbus"        ; dbus-run-session wraps icewm-session for GLib/GIO apps
   "xterm"       ; fallback terminal
   "wine64"      ; WoW64 Wine — runs 32- and 64-bit Windows executables
   "winetricks"  ; Wine helper: installs DLLs, runtimes, vcredist etc.
   ))
;; room-gaming:1 ends here
