;; Channel pin template (seed only once)

;; [[file:../../../guix.org::*Channel pin template (seed only once)][Channel pin template (seed only once):1]]
;; Single source of truth. Tangled only from guix.org.
(list
  (channel
    (name 'guix)
    (url "https://codeberg.org/guix/guix.git")
    (introduction
      (make-channel-introduction
        "9edb3f66fd807b096b48283debdcddccfea34bad"
        (openpgp-fingerprint
         "BBB0 2DDF 2E8C 26C5 7D28  9DDA 013A 06C9 4F2A E8C4"))))
  (channel
    (name 'nonguix)
    (url "https://gitlab.com/nonguix/nonguix")
    (introduction
      (make-channel-introduction
        "897c1a470da759236cc11798f4e0a5f7d4d59fbc"
        (openpgp-fingerprint
         "2A39 3FFF 68F4 EF7A 3D29  12AF 6F51 20A0 22FB B2D5")))))
;; Channel pin template (seed only once):1 ends here
