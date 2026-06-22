;; sanctuary-gnustep

;; Window Maker and GNUstep are installed from apt inside the Debian-based Distrobox
;; container. This Guix manifest holds only Guix-managed complements (if any).
;; Validate which GNUstep/Window Maker packages exist in Guix before filling this in.


;; [[file:../../../../../guix.org::*sanctuary-gnustep][sanctuary-gnustep:1]]
;; Virtual Habitat — sanctuary-gnustep Guix profile
;; Window Maker + GNUstep come from apt inside the Distrobox container.
;; Only Guix-managed complements go here.
;; TODO (Phase 1A): audit Guix package availability with `guix search windowmaker gnustep`
(specifications->manifest
 '(
   ;; "windowmaker"   ; likely not in Guix — use apt inside container
   ;; "gnustep-make"  ; likely not in Guix — use apt inside container
   ))
;; sanctuary-gnustep:1 ends here
