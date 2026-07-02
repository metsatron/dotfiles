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
   "gtk+"     ; GTK schemas, including org.gtk.Settings.FileChooser
   "pluma"    ; MATE text editor for Redstone native apps
   "audacious" ; Winamp-skin-capable audio player
   "pnmixer"  ; lightweight system tray volume applet
   "network-manager-applet" ; tray applet; launched only when NetworkManager is active
   "lxappearance" ; GTK theme/icon settings UI
   "dbus"     ; dbus-run-session wraps icewm-session for GLib/GIO apps
   "gsettings-desktop-schemas" ; schemas required by PCManFM desktop preferences
   "xrdb"     ; load Redstone URxVT Xresources into Xephyr
   "xterm"    ; fallback terminal
   "xdpyinfo"  ; display info
   "xwininfo"  ; window inspection
   "xprop"     ; window/root properties
   "xrandr"    ; display DPI configuration
   ;; --- Redstone 9X accessory + game suite ---
   "mousepad"    ; XFCE text editor — Redstone 9X default text editor
   "tcalc"       ; terminal calculator (Accessories) — launched via xterm -e
   "aisleriot"   ; Solitaire card games: Klondike (default) and FreeCell (--variation=freecell)
   "sdl2"         ; SDL2 runtime — dsdmine (Minesweeper) links against it
   "gnubg"       ; GNU Backgammon (Games)
   "freeciv"     ; FreeCiv turn-based strategy (Games) — client: freeciv-gtk3
   "corsix-th"   ; CorsixTH — open-source Theme Hospital clone (Games)
   "openttd"     ; OpenTTD — Transport Tycoon Deluxe clone (Games)
   "openrct2"    ; OpenRCT2 — RollerCoaster Tycoon 2 clone (Games)
   ))
;; room-gaming:1 ends here
