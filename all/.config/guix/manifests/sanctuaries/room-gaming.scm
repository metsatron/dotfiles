;; room-gaming

;; Shared IceWM desktop stack for gaming-wing sanctuaries.  Pure desktop — no Windows
;; compatibility tools (those live in =room-windows-compat=, sourced separately by
;; Windows-themed rooms like =sanctuary-redstone-9x=).


;; [[file:../../../../../guix.org::*room-gaming][room-gaming:1]]
;; Virtual Habitat — room-gaming Guix profile
;; Desktop stack shared across all gaming-wing sanctuaries.
;; Windows compat tools live in room-windows-compat (sourced separately).
;; Apply: make guix-room-gaming
(specifications->manifest
 '(
   "icewm"    ; Win9x/XP-era WM — Windows-95 theme
   "pcmanfm"  ; GTK file manager (needs dbus session)
   "dbus"     ; dbus-run-session wraps icewm-session for GLib/GIO apps
   "xterm"    ; fallback terminal
   ))
;; room-gaming:1 ends here
