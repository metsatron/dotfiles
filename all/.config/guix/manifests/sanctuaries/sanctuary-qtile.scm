;; sanctuary-qtile

;; Qtile is a Python tiling WM available in Guix. This profile is sourced after
;; =desktop-common= in the =sanctuary-qtile= launcher. Verify package name with
;; =guix search qtile= before applying.


;; [[file:../../../../../guix.org::*sanctuary-qtile][sanctuary-qtile:1]]
;; Virtual Habitat — sanctuary-qtile Guix profile
;; Qtile-specific packages. desktop-common is sourced separately by the launcher.
;; TODO (Phase 1A): validate package names with `guix search qtile` before applying
(specifications->manifest
 '(
   ;; "python-qtile"       ; TODO: validate — Qtile Python WM
   ;; "python-dbus"        ; system tray / notification support in Qtile
   ;; "xterm"              ; fallback terminal inside sanctuary
   ))
;; sanctuary-qtile:1 ends here
