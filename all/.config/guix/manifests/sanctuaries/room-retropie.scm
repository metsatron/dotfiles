;; room-retropie

;; RetroPie sanctuary's runtime profile — the gamepad-first EmulationStation room
;; (=retropie.org=).  Same one-store-many-rooms substrate every other sanctuary
;; uses: packages come from the shared Guix store, not from a bespoke apt
;; rootfs or RetroPie-Setup's own binary/source install path.

;; Audited 2026-07-03 against the live Guix channel (=guix search=/=guix show=,
;; verified not assumed): =retroarch=, =mame=, =mednafen=, and a curated
;; libretro-core spread are real, packaged today. Guix's own =emulation-station=
;; package is the original unmaintained Aloshi upstream (commit-pinned, no
;; release since), *not* the actively-developed RetroPie fork the theme and
;; =es_systems.cfg= actually target — confirmed by reading the package
;; definition's =git-fetch= origin in =gnu/packages/emulators.scm=. The local
;; =retropie-emulationstation= package below (RetroPie's own ES fork, built from
;; source) is used instead.

;; X68000/PC-98/FM-TOWNS marrow: =libretro-px68k= (X68000), =retropie-np2kai=
;; (PC-98), and =retropie-tsugaru= (FM-TOWNS, CUI target only — EmulationStation
;; launches emulator binaries directly and has no use for the GUI variant, which
;; would otherwise need a second pinned git-fetch origin for the
;; =captainys/public= helper repo) are none of them upstream Guix or nonguix
;; packages — packaged locally below, the sovereign-channel path ruling #4
;; calls for, in the same =all/.config/guix/local-packages/= tree =dosbox-x= and
;; =powershell= already use.


;; [[file:../../../../../guix.org::*room-retropie][room-retropie:1]]
;; Virtual Habitat — room-retropie Guix profile
;; RetroPie sanctuary runtime: EmulationStation front-end + RetroArch/libretro
;; cores + MAME + Mednafen, plus the X68000/PC-98/FM-TOWNS marrow.
;; Apply: make guix-room-retropie   (uses -L for local package defs)
(use-modules (gnu packages emulators)      ; retroarch, mame, mednafen, most cores
             (gnu packages games)          ; yamagi-quake2, sdlpop, supertux, openttd (ports engines, 2026-07-12)
             (gnu packages game-development) ; ioquake3
             (nongnu packages emulators)   ; libretro-genesis-plus-gx
             (nongnu packages game-development) ; eduke32, fury (nonguix ruling 2026-07-12)
             (local packages retropie-emulationstation)  ; local: RetroPie ES fork
             (local packages prboom-libretro)             ; local source build: Doom core
             (local packages tyrquake-libretro)           ; local source build: Quake 1 core
             (local packages px68k-libretro)             ; local: X68000 libretro core
             (local packages np2kai)                     ; local: PC-98 (NP2kai/sdlnp21kai)
             (local packages tsugaru))                   ; local: FM-TOWNS (Tsugaru_CUI)

(packages->manifest
 (list retroarch
       mame
       mednafen
       ;; ports engines — sourcing matrix 2026-07-12 (Guix-proper lane)
       yamagi-quake2
       ioquake3
       sdlpop
       supertux
       openttd
       ;; nonguix lane — Mètsàtron's ruling 2026-07-12: guix+nonguix top priority
       eduke32
       fury
       retropie-emulationstation
       libretro-genesis-plus-gx
       libretro-nestopia
       libretro-bsnes-jg
       libretro-mupen64plus-nx
       libretro-beetle-psx-hw
       libretro-flycast
       libretro-beetle-gba
       ;; local source builds — Doom and Quake 1 are absent from Guix/nonguix
       libretro-prboom
       libretro-tyrquake
       libretro-px68k
       retropie-np2kai
       retropie-tsugaru))
;; room-retropie:1 ends here
