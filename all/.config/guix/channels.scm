;; Channel pin, reproducible by time-machine if desired
;; Tangling target: =all/.config/guix/channels.scm=


;; [[file:../../../guix.org::*Channel pin, reproducible by time-machine if desired][Channel pin, reproducible by time-machine if desired:1]]
;; Guix channels for Mètsàtron
(list
  (channel
    (name 'guix)
    (url "https://git.savannah.gnu.org/git/guix.git")
    ;; Optional pin to a commit for stable rollouts. Uncomment to lock.
    ;; (commit "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    )
  ;; Example community channel, disabled by default
  ;; (channel
  ;;   (name 'nonguix)
  ;;   (url "https://gitlab.com/nonguix/nonguix.git"))
)
;; Channel pin, reproducible by time-machine if desired:1 ends here
