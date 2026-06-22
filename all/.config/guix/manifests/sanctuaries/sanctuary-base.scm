;; sanctuary-base

;; Minimal container base for Distrobox compatibility. This is the only manifest that
;; gets packed into a Docker image via =guix pack=. It contains nothing sanctuary-specific —
;; just the system utilities Distrobox needs to function inside a Guix rootfs.

;; Actual packages (qtile, emacs, zsh, etc.) are NOT bundled here. They come from
;; the host =/gnu/store= bind-mounted read-only into the container, accessed via
;; =~/.guix-extra-profiles/= profile symlinks.


;; [[file:../../../../../guix.org::*sanctuary-base][sanctuary-base:1]]
;; Virtual Habitat — sanctuary base layer (container compat only)
;; Packed into a Docker image via `guix pack -f docker`.
;; All actual packages come from the host /gnu/store bind-mount.
;; Keep this manifest minimal — only what Distrobox needs to enter the container.
(specifications->manifest
 '(
   "bash"
   "coreutils"
   "glibc"         ; getent — Distrobox init uses getent passwd heavily; without it the
                   ; elif branch runs with empty current_user_entry and hits exit 1
   "shadow"        ; useradd / passwd / group management — Distrobox requires this
   "util-linux"    ; basic system utilities (mount, login, etc.)
   "findutils"     ; find, xargs
   "grep" "gawk" "sed"
   "diffutils"
   "procps"        ; ps, kill — Distrobox uses these internally
   "which"
   "glibc-locales"
   "nss-certs"
   ))
;; sanctuary-base:1 ends here
