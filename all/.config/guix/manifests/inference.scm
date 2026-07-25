;; Inference profile — CPU-tuned llama.cpp and whisper.cpp

;; Local CPU inference, kept out of =core.scm= on purpose and applied only to machines that
;; should actually run models.

;; *Why this profile exists.* Guix's stock =ggml= and =ggml-for-whisper= are built for baseline
;; x86_64. Disassembling =libggml-cpu.so= from both shows *zero* =%ymm= (AVX/AVX2), *zero* =%zmm=
;; (AVX-512) and *zero* =vfmadd= (FMA) against roughly 13k =%xmm= — pure SSE, on CPUs whose
;; =/proc/cpuinfo= advertises =avx avx2 fma=. ggml's quantized dot-product kernels have
;; hand-written AVX2 paths and fall back to generic scalar C without them. Measured on the
;; T480s: ~13 tok/s embedding locally, against ~890 tok/s from a machine whose llama.cpp was
;; compiled normally (17490 AVX2, 8972 AVX-512, 1861 FMA instructions).

;; *Why not =--tune=.* =guix build --tune=native= prints "tuning llama-cpp for CPU skylake" and
;; "tuning ggml for CPU skylake" and then emits a *byte-identical store path*. It is a verified
;; no-op for these packages and the reassuring message is a trap. =--with-configure-flag= on the
;; ggml packages is the lever that actually produces new derivations.

;; *Why =GGML_CPU_ALL_VARIANTS= and not =GGML_NATIVE=.* The first attempt used
;; =-DGGML_NATIVE=ON= and failed at configure time, with upstream ggml itself naming the answer:
;; "GGML_NATIVE is not compatible with GGML_BACKEND_DL, consider using GGML_CPU_ALL_VARIANTS"
;; (=src/ggml-cpu/CMakeLists.txt:374=). Guix builds these packages with =GGML_BACKEND_DL=ON= and a
;; =GGML_BACKEND_DIR= pointing at =lib/backends=, so the dynamic-backend path is not optional here.

;; That constraint turns out to be a gift. =GGML_CPU_ALL_VARIANTS=ON= compiles a full set of CPU
;; backends — sandybridge, haswell, skylake-x, icelake, alderlake and friends — and ggml picks the
;; best one your CPU supports at load time. So the build is *portable*: one derivation is correct
;; on the T480s and T480 (AVX2), on the T1700's Haswell Xeon when it lands, and on anything added
;; later, with no =-march=native= lock-in and no per-machine divergence. It costs a longer compile
;; (several variants instead of one) and a larger profile, paid once.

;; *Verify, never assume.* A silent regression here looks exactly like success — the profile builds,
;; the binaries run, and they are simply slow. After building, count the vector instructions:
;; =objdump -d ~/.guix-extra-profiles/inference/inference/lib/backends/libggml-cpu-haswell.so | grep -c '%ymm'=
;; A zero means the variant build did not take.

;; *Who gets it.* Machines that do local CPU inference as a fallback when the primary inference
;; node is unreachable: currently the T480s and T480, and the Precision T1700 when it lands
;; (Xeon E3-1246 v3, Haswell — AVX2 + FMA). Deliberately *not* the X230: it is the fleet
;; fileserver, thermally degraded, and does no local inference (ruling 2026-07-25).


;; [[file:../../../../package-guix.org::*Inference profile — CPU-tuned llama.cpp and whisper.cpp][Inference profile — CPU-tuned llama.cpp and whisper.cpp:1]]
;; ~/.config/guix/manifests/inference.scm
;; CPU-tuned local inference. Apply with `loom guix:inference-apply'.
;; Deliberately excluded from core.scm — see the notes in package-guix.org.
(use-modules (gnu packages)
             (guix transformations))

;; ggml and ggml-for-whisper are separate packages carrying the same defect; both need the flag.
;;
;; NOT GGML_NATIVE. Guix builds these with GGML_BACKEND_DL=ON, and ggml's own CMake rejects
;; the combination outright: "GGML_NATIVE is not compatible with GGML_BACKEND_DL, consider
;; using GGML_CPU_ALL_VARIANTS" (src/ggml-cpu/CMakeLists.txt:374). ALL_VARIANTS compiles one
;; backend per microarchitecture and dispatches at load time, which is both what upstream
;; wants here and portable across the whole fleet — no -march=native lock-in.
;;
;; Verify after building, do not assume — a failed variant build still produces a working,
;; merely slow, profile:
;;   objdump -d <profile>/lib/backends/libggml-cpu-haswell.so | grep -c '%ymm'
(define tune-ggml
  (options->transformation
   '((with-configure-flag . "ggml=-DGGML_CPU_ALL_VARIANTS=ON")
     (with-configure-flag . "ggml-for-whisper=-DGGML_CPU_ALL_VARIANTS=ON"))))

(packages->manifest
 (map (compose tune-ggml specification->package)
      (list "llama-cpp"      ; Recall embeddings (Qwen3-Embedding) + local chat fallback
            "whisper-cpp"))) ; whisper-transcribe, whisper-hotkey dictation, telegram voice
;; Inference profile — CPU-tuned llama.cpp and whisper.cpp:1 ends here
