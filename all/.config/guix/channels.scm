;; Channel pin, reproducible by time-machine if desired
;; Tangling target: =all/.config/guix/channels.scm=


;; [[file:../../../guix.org::*Channel pin, reproducible by time-machine if desired][Channel pin, reproducible by time-machine if desired:1]]
;; Guix channels for Mètsàtron (authenticated)
(list
  (channel
    (name 'guix)
    (url "https://git.savannah.gnu.org/git/guix.git")
    (introduction
      (make-channel-introduction
        "9edb3f66fd807b096b48283debdcddccfea34bad"
        (openpgp-fingerprint
         "BBB0 2DDF 2A54 27B3 78B2 6E33 4B04 82B6 6299 CBB6")))))
;; Channel pin, reproducible by time-machine if desired:1 ends here
