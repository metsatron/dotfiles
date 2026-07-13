;; [[file:../../../guix.org::*Channel pin (fleet-wide revision lock)][Channel pin (fleet-wide revision lock):1]]
;; Single source of truth. Tangled only from guix.org.
;; PINNED 2026-07-14 — see guix.org for why this is load-bearing.
(list
  (channel
    (name 'guix)
    (url "https://codeberg.org/guix/guix.git")
    (branch "master")
    (commit "1fef20a1c0c25d887f7abd51e11079a53132fe35")
    (introduction
      (make-channel-introduction
        "9edb3f66fd807b096b48283debdcddccfea34bad"
        (openpgp-fingerprint
         "BBB0 2DDF 2E8C 26C5 7D28  9DDA 013A 06C9 4F2A E8C4"))))
  (channel
    (name 'nonguix)
    (url "https://gitlab.com/nonguix/nonguix")
    (branch "master")
    (commit "3b66965566fe8c96edb5a41fd39a9e5a90ad9b61")
    (introduction
      (make-channel-introduction
        "897c1a470da759236cc11798f4e0a5f7d4d59fbc"
        (openpgp-fingerprint
         "2A39 3FFF 68F4 EF7A 3D29  12AF 6F51 20A0 22FB B2D5")))))
;; Channel pin (fleet-wide revision lock):1 ends here
