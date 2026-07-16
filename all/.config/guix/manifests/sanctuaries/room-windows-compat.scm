;; room-windows-compat

;; Reusable Windows compatibility layer.  Sourced alongside =room-gaming= by any
;; Windows-themed sanctuary (=sanctuary-redstone-9x=, future =lunestone-b2=, etc.).
;; Also consumable by Azure Neptune via its own KVM provisioning path.

;; Categories:
;; - *Guix standard*: =wine64=, =fontconfig=
;; - *nonguix channel*: =winetricks=
;; - *Local package defs* (=all/.config/guix/local-packages/=): =powershell=, =dosbox-x= (integrated Redstone compatibility lane while the =DOSEMU2= package recipe catches up)


;; [[file:../../../../../package-guix.org::*room-windows-compat][room-windows-compat:1]]
;; Virtual Habitat — room-windows-compat Guix profile
;; Windows compatibility layer: Wine, fonts, terminal runtimes, DOS emulation.
;; Redstone's active DOS direction is DOSEMU2 for terminal-clean DOS work, while
;; DOSBox-X remains an integrated compatibility lane for mouse-heavy DOS,
;; Windows 3.x, and booted Win9x profiles until the DOSEMU2 package recipe is declared.
;; Apply: make guix-room-windows-compat   (uses -L for local package defs)
(use-modules (gnu packages wine)          ; wine64
             (nongnu packages wine)       ; winetricks
             (gnu packages fontutils)     ; fontconfig
             (gnu packages xdisorg)       ; rxvt-unicode
             (gnu packages compression)   ; unzip
             (local packages powershell)  ; local: PowerShell 7.x binary
             (local packages dosbox-x))   ; local: DOSBox-X from source

(packages->manifest
 (list wine64 winetricks fontconfig rxvt-unicode unzip powershell dosbox-x))
;; room-windows-compat:1 ends here
