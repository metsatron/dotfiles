;; room-windows-compat

;; Reusable Windows compatibility layer.  Sourced alongside =room-gaming= by any
;; Windows-themed sanctuary (=sanctuary-redstone-9x=, future =lunestone-b2=, etc.).
;; Also consumable by Azure Neptune via its own KVM provisioning path.

;; Categories:
;; - *Guix standard*: =wine64=, =fontconfig=, =icoutils= (=wrestool=/=icotool= — pull icon resources straight out of NE/PE binaries; how the Best of Entertainment Pack menu gets its genuine 1994 icons)
;; - *nonguix channel*: =winetricks=
;; - *Local package defs* (=all/.config/guix/local-packages/=): =powershell=, =dosbox-x= (integrated Redstone compatibility lane for mouse-heavy DOS / Win9x), =dosemu2= (terminal-clean DOS prompt via dj64/FDPP + =comcom32=; pulls in the =thunk_gen= and =fdpp= local defs)


;; [[file:../../../../../package-guix-habitat.org::*room-windows-compat][room-windows-compat:1]]
;; Virtual Habitat — room-windows-compat Guix profile
;; Windows compatibility layer: Wine, fonts, terminal runtimes, DOS emulation.
;; Redstone's active DOS direction is DOSEMU2 for terminal-clean DOS work (dj64
;; kernel/shell relocated from the upstream PPA, with a source-built FDPP), while
;; DOSBox-X remains an integrated compatibility lane for mouse-heavy DOS,
;; Windows 3.x, and booted Win9x profiles.
;; Apply: make guix-room-windows-compat   (uses -L for local package defs)
(use-modules (gnu packages wine)          ; wine64
             (nongnu packages wine)       ; winetricks
             (gnu packages fontutils)     ; fontconfig
             (gnu packages image)         ; icoutils — wrestool/icotool for NE/PE icon resources
             (gnu packages xdisorg)       ; rxvt-unicode
             (gnu packages compression)   ; unzip
             (gnu packages gnome)         ; zenity — winetricks --gui dialog backend
             (local packages powershell)  ; local: PowerShell 7.x binary
             (local packages dosbox-x)    ; local: DOSBox-X from source
             (local packages dosemu2))    ; local: DOSEMU2 (dj64/FDPP) + comcom32

(packages->manifest
 (list wine64 winetricks fontconfig icoutils rxvt-unicode unzip zenity powershell
       dosbox-x dosemu2))
;; room-windows-compat:1 ends here
