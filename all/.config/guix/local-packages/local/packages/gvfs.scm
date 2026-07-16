;; gvfs (patched: "Trash" → "Recycle Bin") — PARKED, not currently used

;; *Not wired into any manifest as of 2026-07-06.* Was merged into =room-gaming=
;; via =concatenate-manifests= but reverted the same day: making =trash:///=
;; resolve for PCManFM's desktop mode exposed a real libfm bug (its
;; =FmFileInfoJob= reads attributes GVFS's trash-root =query_info= never sets —
;; =size=/=is-hidden=/=is-symlink=/etc — without guarding for their absence),
;; reliably crashing =pcmanfm --desktop= shortly after startup. Kept here,
;; unreferenced, for whoever picks the Recycle Bin fix back up — the patch
;; itself is correct (verified via =strings= on the built binary); the
;; blocker is the separate libfm defect, not this package. See
;; =redstone-9x-state-digest.md= for the full diagnosis.

;; Not a new package — a one-string patch on top of upstream Guix's own =gvfs=
;; (=gnu/packages/gnome.scm=, currently 1.58.0), kept in sync via
;; =(inherit gvfs)= rather than a full re-vendor. Redstone 9X's desktop-mode
;; native trash icon (rendered by PCManFM's =pcmanfm --desktop=, backed by
;; GVFS's =trash://= client module) hardcodes the caption "Trash" — confirmed
;; by reading upstream source directly: PCManFM's own
;; =src/desktop.c#_add_extra_item("trash:///")= just runs an async
;; =fm_file_info_job= and displays whatever name GIO returns for that URI; the
;; actual literal lives in GVFS's =daemon/gvfsbackendtrash.c=, at both the root
;; =query_info= handler (=g_file_info_set_display_name (info, _("Trash"))=) and
;; =g_vfs_backend_trash_init= (=g_vfs_backend_set_display_name (vfs_backend,
;; _("Trash"))=). Both are simple gettext-wrapped string literals, not
;; translatable-only — patching the untranslated default source string changes
;; the label everywhere it's read from, no locale work needed.


;; [[file:../../../../../../package-guix-habitat.org::*gvfs (patched: "Trash" → "Recycle Bin") — PARKED, not currently used][gvfs (patched: "Trash" → "Recycle Bin") — PARKED, not currently used:1]]
;;; Local Guix package — gvfs, patched
;;; Base: upstream Guix `gvfs` (gnu/packages/gnome.scm, 1.58.0) — inherited,
;;; not re-vendored, so source/inputs/build-system stay in sync with Guix.
;;; Patch: rename the hardcoded desktop-trash-icon caption "Trash" to
;;; "Recycle Bin" for Redstone 9X's Win9x-authentic desktop.
;;; Upstream source read directly to confirm the two exact call sites:
;;; https://github.com/GNOME/gvfs/blob/master/daemon/gvfsbackendtrash.c

(define-module (local packages gvfs)
  #:use-module (guix packages)
  #:use-module (guix utils)
  #:use-module (guix gexp)
  #:use-module (gnu packages gnome))

(define-public gvfs-recycle-bin
  (package
    (inherit gvfs)
    (name "gvfs-recycle-bin")
    (arguments
     (substitute-keyword-arguments (package-arguments gvfs)
       ((#:phases phases)
        #~(modify-phases #$phases
            (add-after 'unpack 'rename-trash-to-recycle-bin
              (lambda _
                (substitute* "daemon/gvfsbackendtrash.c"
                  (("_\\(\"Trash\"\\)") "_(\"Recycle Bin\")"))))))))))
;; gvfs (patched: "Trash" → "Recycle Bin") — PARKED, not currently used:1 ends here
