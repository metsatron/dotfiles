;; sanctuary-gnustep

;; Window Maker is available in Guix (=windowmaker= 0.96.0). Full GNUstep runtime
;; (gnustep-base, gnustep-gui, gnustep-back) is not in Guix channels — those can be
;; added via source build inside the container in a later phase.


;; [[file:../../../../../package-guix.org::*sanctuary-gnustep][sanctuary-gnustep:1]]
;; Virtual Habitat — sanctuary-gnustep Guix profile
;; Window Maker from Guix. GNUstep runtime (base/gui/back) not in Guix channels;
;; compile from source inside the container in a later phase.
(specifications->manifest
 '(
   "windowmaker"    ; classic NeXT-style WM — in Guix 0.96.0
   "xterm"          ; fallback terminal inside the sanctuary
   ))
;; sanctuary-gnustep:1 ends here
