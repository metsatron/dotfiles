(use-modules (ice-9 ftw)
             (guix packages)
             (guix gexp)
             (guix build-system gnu)
             ((guix licenses) #:prefix license:)
             (gnu packages xorg))

(package
  (name "redstone-nextstep-dock")
  (version "1.0")
  (source
   (local-file
    (string-append (dirname (current-filename)) "/redstone-nextstep-dock.c")
    "redstone-nextstep-dock.c"))
  (build-system gnu-build-system)
  (arguments
   (list #:tests? #f
         #:phases
         #~(modify-phases %standard-phases
             (delete 'unpack)
             (delete 'configure)
             (replace 'build
               (lambda* (#:key source #:allow-other-keys)
                 (invoke #$(cc-for-target) source "-lX11" "-o" "nextstep-dock")))
             (replace 'install
               (lambda _
                 (install-file "nextstep-dock" (string-append #$output "/bin")))))))
  (inputs (list libx11))
  (home-page "https://github.com/Metsatron/DotCortex")
  (synopsis "NeXT logo tile for the Redstone 9X IceWM dock")
  (description "A small Window Maker-compatible X11 dockapp used as the logo tile in Redstone 9X NeXTSTEP Desktop Schemes.")
  (license license:gpl3+))
