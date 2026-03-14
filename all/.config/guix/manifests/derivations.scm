;; [[file:../../../../guix.org::*Guix User profile manifests][Guix User profile manifests:5]]
;; These packages lack substitutions and the derivations.
;; They require extremely heavy local compilation for all dependencies.
;; Tooks 11.5h to compile last time on my X230 turboing @3.4Ghz 92C.

;; What built from source (grouped)
;; Qt 5.15.x stack (big hitter) — triggered by Picard (PyQt5) and partly by KeePassXC:
;; picard-2.13.3 (also pulled quazip-1.5)
   "picard"
   "keepassxc"
;; Qt 6.9.2 stack (another big hitter) — triggered by CoreCtrl and the mGBA Qt frontend:
   "corectrl"
   "mgba"
;; Pandoc + Haskell galaxy (very CPU-intensive) — triggered by pandoc-2.19.2:
   "pandoc"

;; QtDeclarative (both 5.15.16 and 6.9.2) is among the heaviest units here.
;; But the Pandoc/Haskell stack is also a whale when it doesn’t have substitutes.
;; Guix User profile manifests:5 ends here
