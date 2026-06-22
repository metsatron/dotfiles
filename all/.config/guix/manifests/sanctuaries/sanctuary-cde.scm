;; sanctuary-cde

;; Open CDE (=cdesktopenv= / =arcfide/CDesktopEnv=) is compiled from source inside
;; the container. This profile holds Guix-managed build toolchain supplements if
;; needed alongside apt-provided Motif/X11 dependencies.


;; [[file:../../../../../guix.org::*sanctuary-cde][sanctuary-cde:1]]
;; Virtual Habitat — sanctuary-cde Guix profile
;; Open CDE is built from source — Motif/X11/imake deps come from apt.
;; Only Guix-managed build toolchain supplements go here.
;; TODO (Phase 1B): audit which CDE build deps (if any) are better sourced from Guix
(specifications->manifest
 '(
   ;; "motif"    ; OpenMotif — check if available in Guix or use apt libmotif-dev
   ;; "imake"    ; X11 build tool — TODO validate
   ))
;; sanctuary-cde:1 ends here
