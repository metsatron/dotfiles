;; room-gaming

;; Shared profile for gaming-wing sanctuaries.  IceWM is the only confirmed Guix
;; package for the first slice (=sanctuary-redstone-9x=).  Gaming tool stacks (Steam,
;; Lutris, Wine, Proton, DOSBox-X, emulators) are not yet audited for Guix availability
;; — add them here once each is confirmed, never as foreign-distro workarounds.


;; [[file:../../../../../guix.org::*room-gaming][room-gaming:1]]
;; Virtual Habitat — room-gaming Guix profile
;; Shared across gaming-wing sanctuaries (redstone-9x, lunestone-b2, commodore, retropie).
;; desktop-common is sourced separately by each launcher.
;; Apply: make guix-room-gaming   OR   loom guix:sanctuary-apply
(specifications->manifest
 '(
   "icewm"    ; Win9x/XP-era WM — confirmed in Guix; first slice uses Windows-95 theme
   "pcmanfm"  ; GTK file manager — period-appropriate for the Win9x desktop aesthetic
   "xterm"    ; fallback terminal inside gaming sanctuaries
   ))
;; room-gaming:1 ends here
