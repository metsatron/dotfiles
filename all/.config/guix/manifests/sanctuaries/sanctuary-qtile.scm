;; sanctuary-qtile

;; Qtile is a Python tiling WM available in Guix. This profile is sourced after
;; =desktop-common= in the =sanctuary-qtile= launcher. Verify package name with
;; =guix search qtile= before applying.


;; [[file:../../../../../package-guix-habitat.org::*sanctuary-qtile][sanctuary-qtile:1]]
;; Virtual Habitat — sanctuary-qtile Guix profile
;; Qtile-specific packages. desktop-common is sourced separately by the launcher.
;; Apply: guix package -m manifests/sanctuaries/sanctuary-qtile.scm -p ~/.guix-extra-profiles/sanctuary-qtile/sanctuary-qtile
(specifications->manifest
 '(
   "qtile"          ; 0.36.0 — confirmed in Guix (package is `qtile`, not `python-qtile`)
   "python-dbus"    ; system tray / notification support in Qtile
   "xterm"          ; fallback terminal inside sanctuary
   ))
;; sanctuary-qtile:1 ends here
