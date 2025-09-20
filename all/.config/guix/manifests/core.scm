;; User profile manifests
;; Tangling target: =all/.config/guix/manifests/dev.scm= and friends.


;; [[file:../../../../guix.org::*User profile manifests][User profile manifests:1]]
;; Core userland that is safe on a foreign distro
(specifications->manifest
 '(
   "git"
   "htop"
   "ripgrep"
   "fd"
   "jq"
   "direnv"
   "btop"
   "python"
   "node"   ;; small Node for tooling, adjust if you prefer system Node
   ))
;; User profile manifests:1 ends here
