;; room-gaming

;; Shared IceWM desktop stack for gaming-wing sanctuaries.  Pure desktop — no Windows
;; compatibility tools (those live in =room-windows-compat=, sourced separately by
;; Windows-themed rooms like =sanctuary-redstone-9x=).


;; [[file:../../../../../package-guix-habitat.org::*room-gaming][room-gaming:1]]
;; Virtual Habitat — room-gaming Guix profile
;; Desktop stack shared across all gaming-wing sanctuaries.
;; Windows compat tools live in room-windows-compat (sourced separately).
;; NOTE 2026-07-06: gvfs was tried here (plain, then patched via local
;; packages/gvfs.scm to rename its "Trash" desktop caption) to fix the
;; Recycle Bin's "operation not supported" error. Reverted the same day —
;; it exposed a real libfm bug: PCManFM's desktop-mode trash_can creation
;; (src/desktop.c, unconditional at startup once trash:/// resolves) hits
;; a FmFileInfoJob attribute set that GVFS's trash-root query_info never
;; populates (size/is-hidden/is-symlink/etc — only sets type/name/
;; display-name/content-type/icon), and libfm doesn't guard the missing
;; attributes before reading them — PCManFM's desktop process reliably
;; crashed shortly after startup, empty desktop. Never triggered before
;; because room-gaming had no gvfs at all, so trash:/// never resolved and
;; this code path was dormant. See redstone-9x-state-digest.md for the full
;; diagnosis (including an unrelated but real XDG_DATA_DIRS cross-sanctuary
;; leak found and fixed along the way — kept, see room-gaming/room-windows-compat
;; sourcing in sanctuary-distrobox.org). The patched gvfs-recycle-bin package definition
;; is kept, parked, in local packages/gvfs.scm for whoever resumes this.
;; NOTE 2026-07-07: retried PLAIN (unpatched) gvfs to isolate whether the
;; earlier crash was inherent to any gvfs trash backend, or specific to the
;; patched/rebuilt binary from local packages/gvfs.scm. Result: pcmanfm
;; --desktop did NOT crash this time (same GFileInfo attribute warnings as
;; before, so the crash risk is confirmed real and gvfs-version-independent,
;; just intermittent) — but a much worse problem surfaced first: GVFS's
;; trash:// aggregation showed the HOST's real ~/.local/share/Trash/files
;; contents (personal files) inside the sandboxed room, almost certainly via
;; distrobox's /run/host bind mount of the entire host filesystem. That is a
;; sandbox-isolation leak, not a cosmetic bug, and takes priority over the
;; crash question. Reverted again same day. Any future gvfs retry MUST first
;; confirm trash:// isolation holds (no host content visible) before
;; anything else. The desktop-icon "Recycle Bin" workaround (static
;; .desktop + redstone-9x-recycle-bin-watch poller) is disabled, not
;; deleted, in sanctuary-distrobox.org — re-enable it as part of this revert.
;; NOTE 2026-07-07 (3rd attempt, ROOT CAUSE CONFIRMED): re-added plain gvfs
;; to test whether the host-trash leak was caused by long-lived orphaned
;; gvfsd-trash daemons (no init/reaper) carrying stale HOME, rather than a
;; structural filesystem leak. Tested on a COMPLETELY FRESH container
;; (podman kill+start) and fresh session — leak reproduced immediately, so
;; the orphan theory is wrong. Root cause, confirmed via `gio list trash:///`
;; with the correct in-session D-Bus address and GIO_EXTRA_MODULES pointing
;; at gvfs's own libgvfsdbus.so: distrobox's /run/host bind mount is
;; RECURSIVE — it carries every filesystem mounted underneath the host root
;; into the container's own mount table, not just the host root itself.
;; GVFS's trash aggregator (GUnixMountMonitor) walks every mount point it
;; can see in ITS OWN mount namespace and checks each one for a
;; .Trash-<uid>/files directory. It found the host's ~/mnt/x230 network
;; mount bridged in at /run/host/home/metsatron/mnt/x230, which has a real
;; .Trash-1000 on it, and merged its real personal files (voice messages,
;; vault notes, etc.) into this sandboxed room's trash:/// view. This is
;; structural, not an orphan-daemon artifact, and will recur on ANY fresh
;; boot as long as gvfs + distrobox's recursive /run/host coexist. Reverted
;; again same day. Do not retry without either (a) a non-recursive /run/host
;; bind (would need distrobox/podman changes upstream), or (b) abandoning
;; gvfs-based trash in sandboxes entirely in favor of the non-GVFS
;; icon-watcher workaround — see redstone-9x-state-digest.md.
;; NOTE 2026-07-08 (leak blocker LIFTED, but gvfs still kept out HERE):
;; sanctuary-trash-shield (sanctuary-distrobox.org) now closes the isolation leak at
;; launch — it make-rprivate's distrobox's passthrough parents and tmpfs-masks
;; the whole ~/mnt tree inside the container's own namespace, so gvfsd-trash
;; can no longer see any foreign fleet mount (this is effectively option (a),
;; done container-side without upstream changes; sanctuary-godzilla-xs re-enabled gvfs
;; on top of it and is safe). gvfs nonetheless stays OUT of room-gaming for an
;; INDEPENDENT reason: the PCManFM/libfm desktop-mode crash above (unguarded
;; missing GVFS trash-root attributes) is intermittent and unfixed, and
;; Redstone 9X already has a working non-GVFS Recycle Bin (the static .desktop
;; + redstone-9x-recycle-bin-watch poller, R9X-TODO-020/021). Re-adding gvfs
;; here would trade a working Recycle Bin for that crash risk with no gain.
;; Re-enable gvfs in a PCManFM room ONLY after the libfm attribute-guard crash
;; is fixed; a Thunar/Nautilus room needs only the shield (see sanctuary-godzilla-xs).
;; Apply: make guix-room-gaming
(use-modules (ice-9 ftw)
             (guix packages)
             (guix gexp)
             (guix utils)
             (guix download)
             (guix build-system copy)
             (guix build-system gnu)
             (guix build-system python)
             (guix build-system trivial)  ; gzdoom-engines union (symlink-only output)
             ((guix licenses) #:prefix license:)
             (gnu packages base)
             (gnu packages crypto)
             (gnu packages lxde)
             (gnu packages wm)          ; icewm — base for icewm-gradients
             (gnu packages xdisorg)
             (gnu packages gnome)       ; gtk+-2, libglade, gnome-vfs, libgnome, gconf, libgtop — netactview deps
             (gnu packages gtk)
             (gnu packages glib)
             (gnu packages libffi)
             (gnu packages pkg-config)
             (gnu packages python)
             (gnu packages games)       ; uzdoom — recipe base for pinned gzdoom engines
             (gnu packages gl)          ; mesa — libGL RUNPATH for pinned gzdoom
             (guix download)            ; url-fetch for pinned engine tarballs
             (guix gexp)
             (gnu packages gettext))

(define pcmanfm-redstone-desktop-labels-patch
  (local-file
   (string-append (dirname (current-filename))
                  "/../../patches/pcmanfm-redstone-desktop-labels.patch")
   "pcmanfm-redstone-desktop-labels.patch"))

;; IceWM with compile-time gradient support. Guix's flags omit
;; CONFIG_GRADIENTS, so Gradients=-listed title pixmaps TILE instead of
;; interpolating (verified live 2026-07-19: 2px colour-stop images rendered
;; as pinstripes). With this ON, tiny colour-stop pixmaps become smooth
;; full-width titlebar gradients — the Windows 98 / Serenity requirement.
(define icewm-gradients
  (package
    (inherit icewm)
    (name "icewm-gradients")
    (arguments
     (substitute-keyword-arguments (package-arguments icewm)
       ((#:configure-flags flags)
        #~(cons "-DCONFIG_GRADIENTS=ON" #$flags))))))

;; IceWM Control Panel 3.2 is the final upstream release (2004).  Its GTK2
;; interface and every bundled applet are Python 2/PyGTK 2 programs.  Current
;; Guix still carries Python 2 and GTK2, but no longer carries the three Python
;; bindings, so keep their last Guix-packaged releases local to this room.
;; All four packages were built together against the pinned channel commit
;; 1fef20a1c0c25d887f7abd51e11079a53132fe35 before landing here.
(define python2-pycairo-legacy
  (package
    (name "python2-pycairo")
    (version "1.18.2")
    (source
     (origin
       (method url-fetch)
       (uri (string-append "https://github.com/pygobject/pycairo/releases/"
                           "download/v" version "/pycairo-" version ".tar.gz"))
       (sha256
        (base32 "0cb5n4r4nl0k1g90b1gz9iyk4lp7hi03db98i1p52a870bym7f6w"))))
    (build-system python-build-system)
    (arguments (list #:python python-2 #:tests? #f))
    (native-inputs (list pkg-config libxcrypt))
    (propagated-inputs (list cairo))
    (home-page "https://cairographics.org/pycairo/")
    (synopsis "Legacy Python 2 bindings for Cairo")
    (description "Pycairo provides Python bindings for the Cairo graphics library.")
    (license (list license:lgpl2.1 license:mpl1.1))))

(define python2-pygobject-2-legacy
  (package
    (name "python2-pygobject")
    (version "2.28.7")
    (source
     (origin
       (method url-fetch)
       (uri (string-append "mirror://gnome/sources/pygobject/"
                           (version-major+minor version) "/pygobject-" version ".tar.xz"))
       (sha256
        (base32 "0nkam61rsn7y3wik3vw46wk5q2cjfh2iph57hl9m39rc8jijb7dv"))))
    (build-system gnu-build-system)
    (native-inputs (list which (list glib "bin") pkg-config dbus libxcrypt))
    (inputs (list python-2 glib python2-pycairo-legacy gobject-introspection))
    (propagated-inputs (list libffi))
    (arguments
     (list #:tests? #f
           #:configure-flags #~(list "LIBS=-lcairo-gobject")
           #:phases
           #~(modify-phases %standard-phases
               (add-after 'unpack 'remove-obsolete-error-domain-enum
                 (lambda _
                   (substitute* "gi/pygi-info.c"
                     (((string-append "[[:blank:]]*case GI_INFO_TYPE_ERROR_DOMAIN:\\n"
                                      "[[:blank:]]*type = &PyGIErrorDomainInfo_Type;\\n"
                                      "[[:blank:]]*break;\\n")) "")
                     (("[[:blank:]]*case GI_INFO_TYPE_ERROR_DOMAIN:\\n") "")))))))
    (home-page "https://pypi.org/project/PyGObject/")
    (synopsis "Legacy Python 2 bindings for GObject")
    (description "Legacy Python 2 bindings for GLib, GObject, and GIO.")
    (license license:lgpl2.1+)))

(define python2-pygtk-legacy
  (package
    (name "python2-pygtk")
    (version "2.24.0")
    (source
     (origin
       (method url-fetch)
       (uri (string-append "mirror://gnome/sources/pygtk/"
                           (version-major+minor version) "/pygtk-" version ".tar.bz2"))
       (sha256
        (base32 "04k942gn8vl95kwf0qskkv6npclfm31d78ljkrkgyqxxcni1w76d"))))
    (build-system gnu-build-system)
    (outputs '("out" "doc"))
    (native-inputs (list pkg-config libxcrypt))
    (inputs (list python-2 pango-1.42 libglade glib))
    (propagated-inputs
     (list python2-pycairo-legacy python2-pygobject-2-legacy gtk+-2))
    (arguments
     (list #:tests? #f
           #:phases
           #~(modify-phases %standard-phases
               (add-before 'configure 'set-gtk-doc-directory
                 (lambda* (#:key outputs #:allow-other-keys)
                   (substitute* "docs/Makefile.in"
                     (("TARGET_DIR = \\$\\(datadir\\)")
                      (string-append "TARGET_DIR = " (assoc-ref outputs "doc"))))))
               (add-after 'configure 'fix-codegen
                 (lambda* (#:key inputs #:allow-other-keys)
                   (substitute* "pygtk-codegen-2.0"
                     (("^prefix=.*$")
                      (string-append "prefix="
                                     (assoc-ref inputs "python2-pygobject")
                                     "\\n")))))
               (add-after 'install 'install-pth
                 (lambda* (#:key outputs #:allow-other-keys)
                   (let ((site (string-append (assoc-ref outputs "out")
                                              "/lib/python2.7/site-packages")))
                     (call-with-output-file (string-append site "/pygtk.pth")
                       (lambda (port) (format port "gtk-2.0~%")))))))))
    (home-page "http://www.pygtk.org/")
    (synopsis "Legacy Python 2 bindings for GTK 2")
    (description "PyGTK provides Python 2 bindings for GTK 2.")
    (license license:lgpl2.1+)))

(define icewm-control-panel
  (package
    (name "icewm-control-panel")
    (version "3.2")
    (source
     (origin
       (method url-fetch)
       (uri (string-append
             "mirror://sourceforge/icesoundmanager/Control%20Panel/IceWMCP-3.2/"
             "IceWMControlPanel-" version ".tar.bz2"))
       (sha256
        (base32 "1yasj9f0h0f37lv0c5zgcrbhazd7ddh1gb2w4jdh8lg1bmxx4nb2"))))
    (build-system copy-build-system)
    (arguments
     (list #:install-plan #~'(("." "share/icewmcp"))
           #:phases
           #~(modify-phases %standard-phases
               (add-after 'unpack 'patch-runtime-paths
                 (lambda* (#:key inputs #:allow-other-keys)
                   (let ((python (search-input-file inputs "/bin/python2")))
                     (substitute* "launcher.py"
                       (("^#! /usr/bin/env python$") (string-append "#!" python)))
                     ;; Upstream source is ISO-8859-1, which substitute* must
                     ;; be told explicitly before it can patch the file.
                     (with-fluids ((%default-port-encoding "ISO-8859-1"))
                       (substitute* "icewmcp_common.py"
                         (("^def getBaseDir\\(\\) :$")
                          (string-append
                           "def getBaseDir() :\n"
                           "\treturn os.path.dirname(os.path.realpath(sys.argv[0]))+os.sep"))
                         ;; IceWM 4.x uses ICEWM_PRIVCFG.  Retain the old
                         ;; misspelled variable as a compatibility fallback.
                         (("if os.environ.has_key\\(\"ICEWM_PRVCFG\"\\):[[:blank:]]+ppath=os.environ\\['ICEWM_PRVCFG'\\]")
                          "if os.environ.has_key(\"ICEWM_PRIVCFG\"): ppath=os.environ['ICEWM_PRIVCFG']\n\telif os.environ.has_key(\"ICEWM_PRVCFG\"): ppath=os.environ['ICEWM_PRVCFG']"))
                       ;; Replace two extinct optional programs with the
                       ;; maintained equivalents already carried by Redstone.
                       (substitute* "applets/gtop.cpl"
                         (("^Exec=gtop") "Exec=lxtask"))
                       (substitute* "applets/soundprop.cpl"
                         (("^Exec=gtkaumix") "Exec=pavucontrol"))))))
               (add-after 'install 'install-launchers-and-icon
                 (lambda* (#:key outputs #:allow-other-keys)
                   (let* ((out (assoc-ref outputs "out"))
                          (bin (string-append out "/bin"))
                          (icons (string-append out "/share/icons/hicolor/48x48/apps"))
                          (launcher (string-append out "/share/icewmcp/launcher.py"))
                          (python-path (getenv "GUIX_PYTHONPATH")))
                     (mkdir-p bin)
                     (mkdir-p icons)
                     (install-file "icewmcp.png" icons)
                     (rename-file (string-append icons "/icewmcp.png")
                                  (string-append icons "/icewm-control-panel.png"))
                     (chmod launcher #o755)
                     ;; Menu launches do not inherit Guix's build-time Python
                     ;; search path, so preserve the complete PyGTK closure in
                     ;; the installed wrapper.
                     (wrap-program launcher
                       `("GUIX_PYTHONPATH" ":" prefix (,python-path)))
                     (symlink launcher (string-append bin "/IceWMCP"))
                     (symlink launcher (string-append bin "/icewm-control-panel"))))))))
    (inputs (list python-2 python2-pygtk-legacy))
    (home-page "https://icesoundmanager.sourceforge.net/")
    (synopsis "Classic GTK 2 control panel for IceWM")
    (description
     "IceWMCP is a modular Windows Control Panel-style GTK 2 configuration
suite for IceWM.  This package preserves all bundled applets, help, locales,
icons, and applet definitions from the final 3.2 release.")
    (license license:gpl2+)))

;; Netactview 0.6.4 (2015, last upstream release) — GTK2 graphical netstat
;; viewer. IceWM taskbar's Net meter (redstone-9x IceWM prefs,
;; NetStatusCommand="netactview") had no real binary behind it before this;
;; the launcher pointed at a program that did not exist in the room-gaming
;; profile. Upstream (netactview.sourceforge.net) ships only an autotools
;; tarball with a single PKG_CHECK_MODULES pulling in the full GNOME 2 stack
;; (gtk+-2.0, libglade-2.0, gnome-vfs-2.0, glib-2.0, libgnome-2.0, gconf-2.0,
;; libgtop-2.0 — verified against the shipped configure.ac, no optional/soft
;; deps). All seven are still packaged in Guix main. Verified 2026-07-19 with
;; `guix build -f` against an isolated package expression before folding into
;; this manifest — build succeeded end to end (configure/build/install/strip/
;; validate-runpath), output store path
;; /gnu/store/yjpzmwdbbvjbwaqn9g9bjrs69fcllkc7-netactview-0.6.4.
(define netactview
  (package
    (name "netactview")
    (version "0.6.4")
    (source
     (origin
       (method url-fetch)
       (uri (string-append "mirror://sourceforge/netactview/netactview/"
                            "netactview-" version "/netactview-" version
                            ".tar.bz2"))
       (sha256
        (base32
         "0jpv8c4fkv0kkj0rl1p403dfx1wq0xx9gi1cmcchmcb213lnizhc"))))
    (build-system gnu-build-system)
    (arguments
     (list #:tests? #f))               ; upstream ships no test suite
    (native-inputs
     (list pkg-config intltool gettext-minimal))
    (inputs
     (list gtk+-2 libglade gnome-vfs libgnome gconf libgtop glib))
    (synopsis "Graphical network connections viewer")
    (description
     "Netactview is a graphical network connections viewer, similar in
functionality to netstat, with additional features such as per-connection
process information (path, size, owner) and pattern-based filtering.")
    (home-page "https://netactview.sourceforge.net/")
    (license license:gpl2+)))

;; PCManFM 1.4.0 draws the FmDesktop selection and rubber band itself.  Give
;; that custom GtkWindow a unique CSS node, lower its internal background
;; provider from USER to APPLICATION priority, and render the rubber band via
;; GTK's rubberband class.  GDK damage is normally painted later from an idle
;; handler, so process each active drag update before button release can clear
;; rubber_bending and suppress the queued rectangle.  Keep the patch local to
;; this period desktop profile.
(define pcmanfm-redstone
  (package
    (inherit pcmanfm)
    (name "pcmanfm-redstone")
    (arguments
     (list #:configure-flags #~(list "--with-gtk=3")
           #:phases
           #~(modify-phases %standard-phases
            (add-after 'unpack 'apply-desktop-label-rendering
              (lambda _
                (invoke "patch" "-p1" "-i"
                        #$pcmanfm-redstone-desktop-labels-patch)))
            (add-after 'unpack 'fix-desktop-selection-rendering
              (lambda _
                (substitute* "src/desktop.c"
                  (("GTK_STYLE_PROVIDER_PRIORITY_USER")
                   "GTK_STYLE_PROVIDER_PRIORITY_APPLICATION")
                  (("    typedef gboolean")
                   (string-append
                    "#if GTK_CHECK_VERSION(3, 20, 0)\n"
                    "    gtk_widget_class_set_css_name(widget_class, \"fmdesktop\");\n"
                    "#endif\n"
                    "    typedef gboolean"))
                  (("    GdkColor clr;")
                   (string-append
                    "    GdkRectangle clip;\n"
                    "#if GTK_CHECK_VERSION(3, 0, 0)\n"
                    "    GtkStyleContext *style;\n"
                    "#else\n"
                    "    GdkColor clr;"))
                  (("    guchar alpha;")
                   "    guchar alpha;\n#endif")
                  (("    if\\(!gdk_rectangle_intersect\\(expose_area, &rect, &rect\\)\\)")
                   "    if(!gdk_rectangle_intersect(expose_area, &rect, &clip))")
                  (("    clr = gtk_widget_get_style \\(widget\\)->base\\[GTK_STATE_SELECTED\\];")
                   (string-append
                    "#if GTK_CHECK_VERSION(3, 0, 0)\n"
                    "    style = gtk_widget_get_style_context(widget);\n"
                    "    cairo_save(cr);\n"
                    "    gdk_cairo_rectangle(cr, &clip);\n"
                    "    cairo_clip(cr);\n"
                    "    gtk_style_context_save(style);\n"
                    "    gtk_style_context_add_class(style, GTK_STYLE_CLASS_RUBBERBAND);\n"
                    "    gtk_render_background(style, cr, rect.x, rect.y, rect.width, rect.height);\n"
                    "    gtk_render_frame(style, cr, rect.x, rect.y, rect.width, rect.height);\n"
                    "    gtk_style_context_restore(style);\n"
                    "    cairo_restore(cr);\n"
                    "    return;\n"
                    "#else\n"
                    "    clr = gtk_widget_get_style (widget)->base[GTK_STATE_SELECTED];"))
                  (("    cairo_rectangle \\(cr, rect.x \\+ 0.5, rect.y \\+ 0.5, rect.width - 1, rect.height - 1\\);")
                   (string-append
                    "    cairo_rectangle (cr, rect.x + 0.5, rect.y + 0.5, rect.width - 1, rect.height - 1);\n"
                    "#endif"))
                  (("        update_rubberbanding\\(self, evt->x, evt->y\\);")
                   (string-append
                    "        update_rubberbanding(self, evt->x, evt->y);\n"
                    "#if GTK_CHECK_VERSION(3, 0, 0)\n"
                    "        /* Paint active drag damage before release clears the flag. */\n"
                    "        gdk_window_process_updates(gtk_widget_get_window(w), FALSE);\n"
                    "#endif")))
                (invoke "grep" "-q"
                        "gtk_widget_class_set_css_name(widget_class, \"fmdesktop\")"
                        "src/desktop.c")
                (invoke "grep" "-q"
                        "gtk_style_context_add_class(style, GTK_STYLE_CLASS_RUBBERBAND)"
                        "src/desktop.c")
                (invoke "grep" "-q"
                        "gdk_window_process_updates(gtk_widget_get_window(w), FALSE)"
                        "src/desktop.c"))))))))

;; Stock XOSD deliberately creates an override-redirect window and then raises
;; it to the top of the X stack.  That is correct for volume notifications but
;; wrong for Redstone's desktop build stamp.  This room-local variant preserves
;; the shaped override-redirect root child, but maps without raising and places
;; it immediately above PCManFM's root-level desktop sibling.  Root property and
;; structure notifications maintain that relation without involving IceWM.  An
;; empty input shape makes the glyphs click-through.
(define xosd-redstone
  (package
    (inherit xosd)
    (name "xosd-redstone")
    (arguments
     (substitute-keyword-arguments (package-arguments xosd)
       ((#:phases phases #~%standard-phases)
        #~(modify-phases #$phases
            (add-after 'unpack 'make-desktop-layer-window
              (lambda _
                (substitute* "src/libxosd/xosd.c"
                  (("/\\* Handles X11 events, timeouts and does the drawing\\. \\{\\{\\{")
                   (string-append
                    "/* Return true when WINDOW has WANTED in an XA_ATOM property. */\n"
                    "static int\n"
                    "window_has_atom(Display *dpy, Window window, Atom property, Atom wanted)\n"
                    "{\n"
                    "  Atom actual_type;\n"
                    "  int actual_format;\n"
                    "  unsigned long nitems, bytes_after, i;\n"
                    "  unsigned char *data = NULL;\n"
                    "  int found = 0;\n\n"
                    "  if (XGetWindowProperty(dpy, window, property, 0, 4096, False,\n"
                    "                         XA_ATOM, &actual_type, &actual_format,\n"
                    "                         &nitems, &bytes_after, &data) == Success &&\n"
                    "      actual_type == XA_ATOM && actual_format == 32 && data) {\n"
                    "    Atom *atoms = (Atom *) data;\n"
                    "    for (i = 0; i < nitems; i++)\n"
                    "      if (atoms[i] == wanted) { found = 1; break; }\n"
                    "  }\n"
                    "  if (data) XFree(data);\n"
                    "  return found;\n"
                    "}\n\n"
                    "static int\n"
                    "is_pcmanfm_window(Display *dpy, Window window)\n"
                    "{\n"
                    "  XClassHint hint;\n"
                    "  int found = 0;\n\n"
                    "  memset(&hint, 0, sizeof(hint));\n"
                    "  if (XGetClassHint(dpy, window, &hint)) {\n"
                    "    if ((hint.res_name &&\n"
                    "         (strstr(hint.res_name, \"pcmanfm\") ||\n"
                    "          strstr(hint.res_name, \"PCManFM\") ||\n"
                    "          strstr(hint.res_name, \"Pcmanfm\"))) ||\n"
                    "        (hint.res_class &&\n"
                    "         (strstr(hint.res_class, \"pcmanfm\") ||\n"
                    "          strstr(hint.res_class, \"PCManFM\") ||\n"
                    "          strstr(hint.res_class, \"Pcmanfm\"))))\n"
                    "      found = 1;\n"
                    "    if (hint.res_name) XFree(hint.res_name);\n"
                    "    if (hint.res_class) XFree(hint.res_class);\n"
                    "  }\n"
                    "  return found;\n"
                    "}\n\n"
                    "static Window\n"
                    "desktop_client_for(Display *dpy, Window root)\n"
                    "{\n"
                    "  Atom stacking = XInternAtom(dpy, \"_NET_CLIENT_LIST_STACKING\", False);\n"
                    "  Atom desktop = XInternAtom(dpy, \"_NET_WM_WINDOW_TYPE_DESKTOP\", False);\n"
                    "  Atom window_type = XInternAtom(dpy, \"_NET_WM_WINDOW_TYPE\", False);\n"
                    "  Atom actual_type;\n"
                    "  int actual_format;\n"
                    "  unsigned long nitems, bytes_after, i;\n"
                    "  unsigned char *data = NULL;\n"
                    "  Window result = None;\n\n"
                    "  if (XGetWindowProperty(dpy, root, stacking, 0, 4096, False, XA_WINDOW,\n"
                    "                         &actual_type, &actual_format, &nitems,\n"
                    "                         &bytes_after, &data) == Success &&\n"
                    "      actual_type == XA_WINDOW && actual_format == 32 && data) {\n"
                    "    Window *clients = (Window *) data;\n"
                    "    for (i = 0; i < nitems; i++) {\n"
                    "      XWindowAttributes attrs;\n"
                    "      if (XGetWindowAttributes(dpy, clients[i], &attrs) &&\n"
                    "          attrs.map_state == IsViewable &&\n"
                    "          window_has_atom(dpy, clients[i], window_type, desktop) &&\n"
                    "          is_pcmanfm_window(dpy, clients[i])) {\n"
                    "        result = clients[i];\n"
                    "        break;\n"
                    "      }\n"
                    "    }\n"
                    "  }\n"
                    "  if (data) XFree(data);\n"
                    "  return result;\n"
                    "}\n\n"
                    "static Window\n"
                    "root_child_for(Display *dpy, Window window, Window expected_root)\n"
                    "{\n"
                    "  Window root = None, parent = None, *children = NULL;\n"
                    "  unsigned int nchildren = 0;\n\n"
                    "  while (window != None &&\n"
                    "         XQueryTree(dpy, window, &root, &parent, &children, &nchildren)) {\n"
                    "    if (children) XFree(children);\n"
                    "    if (parent == expected_root) return window;\n"
                    "    if (parent == None || parent == window) break;\n"
                    "    window = parent;\n"
                    "  }\n"
                    "  return None;\n"
                    "}\n\n"
                    "static int\n"
                    "stack_above_desktop(Display *dpy, Window stamp, Window desktop_sibling)\n"
                    "{\n"
                    "  XWindowChanges changes;\n"
                    "  memset(&changes, 0, sizeof(changes));\n"
                    "  changes.sibling = desktop_sibling;\n"
                    "  changes.stack_mode = Above;\n"
                    "  XConfigureWindow(dpy, stamp, CWSibling | CWStackMode, &changes);\n"
                    "  XSync(dpy, False);\n"
                    "  return 0;\n"
                    "}\n\n"
                    "static int\n"
                    "maintain_desktop_stack(xosd *osd)\n"
                    "{\n"
                    "  Window root = XRootWindow(osd->display, osd->screen);\n"
                    "  Window client = desktop_client_for(osd->display, root);\n"
                    "  Window sibling = root_child_for(osd->display, client, root);\n\n"
                    "  if (client == None || sibling == None) {\n"
                    "    XUnmapWindow(osd->display, osd->window);\n"
                    "    XFlush(osd->display);\n"
                    "    return -1;\n"
                    "  }\n"
                    "  XMapWindow(osd->display, osd->window);\n"
                    "  XFlush(osd->display);\n"
                    "  return stack_above_desktop(osd->display, osd->window, sibling);\n"
                    "}\n\n"
                    "static int\n"
                    "desktop_stack_event(xosd *osd, XEvent *event)\n"
                    "{\n"
                    "  Window root = XRootWindow(osd->display, osd->screen);\n"
                    "  Atom stacking = XInternAtom(osd->display,\n"
                    "                              \"_NET_CLIENT_LIST_STACKING\", False);\n\n"
                    "  switch (event->type & 0x7f) {\n"
                    "  case PropertyNotify:\n"
                    "    return event->xproperty.window == root &&\n"
                    "           event->xproperty.atom == stacking;\n"
                    "  case ConfigureNotify:\n"
                    "    if (event->xconfigure.window == osd->window) return 0;\n"
                    "    if (event->xconfigure.window == root) {\n"
                    "      osd->screen_width = event->xconfigure.width;\n"
                    "      osd->screen_height = event->xconfigure.height;\n"
                    "      osd->screen_xpos = 0;\n"
                    "      osd->update |= UPD_size | UPD_pos | UPD_mask | UPD_lines;\n"
                    "    }\n"
                    "    return 1;\n"
                    "  case MapNotify:\n"
                    "    return event->xmap.window != osd->window;\n"
                    "  case UnmapNotify:\n"
                    "    return event->xunmap.window != osd->window;\n"
                    "  case ReparentNotify:\n"
                    "    return event->xreparent.window != osd->window;\n"
                    "  case CirculateNotify:\n"
                    "    return event->xcirculate.window != osd->window;\n"
                    "  case DestroyNotify:\n"
                    "    return event->xdestroywindow.window != osd->window;\n"
                    "  default:\n"
                    "    return 0;\n"
                    "  }\n"
                    "}\n\n"
                    "/* Handles X11 events, timeouts and does the drawing. {{{"))
                  (("  XSetWindowAttributes setwinattr;")
                   (string-append
                    "  XSetWindowAttributes setwinattr;\n"
                    "  XClassHint class_hint;"))
                  (("  XStoreName\\(osd->display, osd->window, \"XOSD\"\\);")
                   (string-append
                    "  XStoreName(osd->display, osd->window, \"Redstone Build Stamp\");\n"
                    "  class_hint.res_name = \"redstone-buildstamp\";\n"
                    "  class_hint.res_class = \"RedstoneBuildstamp\";\n"
                    "  XSetClassHint(osd->display, osd->window, &class_hint);"))
                  (("  stay_on_top\\(osd->display, osd->window\\);")
                   "  /* Redstone maintains root-sibling stacking in event_loop. */")
                  (("  XSelectInput\\(osd->display, osd->window, ExposureMask\\);")
                   (string-append
                    "  XSelectInput(osd->display, osd->window, ExposureMask);\n"
                    "  XSelectInput(osd->display,\n"
                    "               XRootWindow(osd->display, osd->screen),\n"
                    "               PropertyChangeMask | SubstructureNotifyMask |\n"
                    "               StructureNotifyMask);"))
                  (("        XMapRaised\\(osd->display, osd->window\\);")
                   "        maintain_desktop_stack(osd);")
                  (("                        osd->mask_bitmap, ShapeSet\\);")
                   (string-append
                    "                        osd->mask_bitmap, ShapeSet);\n"
                    "#ifdef ShapeInput\n"
                    "      XShapeCombineRectangles(osd->display, osd->window, ShapeInput,\n"
                    "                              0, 0, NULL, 0, ShapeSet, Unsorted);\n"
                    "#endif"))
                  (("        DEBUG\\(Dvalue, \"XEvent=%d\", report.type\\);")
                   (string-append
                    "        if (desktop_stack_event(osd, &report)) {\n"
                    "        XEvent queued;\n"
                    "        while (XCheckMaskEvent(osd->display,\n"
                    "                               PropertyChangeMask |\n"
                    "                               SubstructureNotifyMask |\n"
                    "                               StructureNotifyMask, &queued))\n"
                    "          desktop_stack_event(osd, &queued);\n"
                    "        if (osd->generation & 1) maintain_desktop_stack(osd);\n"
                    "        }\n"
                    "        DEBUG(Dvalue, \"XEvent=%d\", report.type);")))
                (invoke "grep" "-q" "setwinattr.override_redirect = 1" "src/libxosd/xosd.c")
                (invoke "grep" "-q" "RedstoneBuildstamp" "src/libxosd/xosd.c")
                (invoke "grep" "-q" "maintain_desktop_stack" "src/libxosd/xosd.c")
                (invoke "grep" "-q" "ShapeInput" "src/libxosd/xosd.c")
                (invoke "grep" "-q" "XMapWindow" "src/libxosd/xosd.c")
                (invoke "grep" "-q" "CWSibling | CWStackMode" "src/libxosd/xosd.c")
                (invoke "grep" "-q" "XCheckMaskEvent" "src/libxosd/xosd.c")
                (when (zero? (system* "grep" "-q" "XMapRaised" "src/libxosd/xosd.c"))
                  (error "Redstone XOSD still contains XMapRaised"))))))))))

;; Version-exact pinned GZDoom engines for the RetroPie ports contracts.
;;
;; The ports .sh scripts pin specific engine builds (gzdoom 4.5.0 for 289
;; launchers, 4.10.0 for 194) because mod/TC ZScript behaviour drifts across
;; engine versions — the pin IS the contract (verified live 2026-07-23: uzdoom
;; 4.14 drew ZScript return-value warnings against LiTDooM). The x230-built FHS
;; bundles cannot run in the Guix guest (no /lib64 loader; libGL bound to the
;; wrong driver stack — the GLX wall). Building version-exact from the ZDoom
;; tag against Guix's own Mesa clears that wall: proven live rendering DOOM 2 at
;; 1024x819 in-guest, 2026-07-23. lutris-ports-bridge resolves gzdoom/* scripts
;; to these instead of the paired-loader fallback.
;;
;; make-gzdoom: one tag + one hash per pinned version. Inherits uzdoom's proven
;; recipe; patches (1) the pk3 store search path — gzdoom persists it to
;; ~/.config/gzdoom/gzdoom.ini and reads it back, so a stale ini shadows a
;; rebuilt engine (sealed as a gotcha); (2) <cstdio> into the vendored AMD VMA
;; header, which GCC 14 no longer includes transitively.
;;
;; Outputs are VERSION-NAMESPACED (bin/gzdoom-<v>, share/games/gzdoom-<v>) so
;; multiple pinned engines coexist in the room-gaming profile without colliding
;; on bin/gzdoom + share/games/doom/gzdoom.pk3. The ports engine resolver maps a
;; script's ./bin/gzdoom-<v>/ dir to the profile's gzdoom-<v> binary.
(define* (make-gzdoom version hash #:key (tarball-version version))
  (package
    (inherit uzdoom)
    (name "gzdoom")
    (version version)
    (source
     (origin
       (method url-fetch)
       (uri (string-append "https://github.com/ZDoom/gzdoom/archive/g"
                           tarball-version ".tar.gz"))
       (file-name (string-append "gzdoom-" version ".tar.gz"))
       (sha256 (base32 hash))
       (modules '((guix build utils)))
       (snippet
        #~(begin
            (substitute* "src/gameconfigfile.cpp"
              (("SetValueForKey \\(\"Path\", \"/usr/local/share/doom\", true\\);" line)
               (string-append
                "SetValueForKey (\"Path\", \"$GUIX_GZDOOM_PREFIX/share/games/gzdoom-"
                #$version "\", true);\n\t\t" line)))
            (substitute* "src/common/rendering/vulkan/thirdparty/vk_mem_alloc/vk_mem_alloc.h"
              (("#include <cstring>")
               "#include <cstring>\n#include <cstdio>"))
            ;; 4.5.0's src/CMakeLists.txt has a POST_BUILD `link-make` symlink
            ;; step that calls the absolute /bin/sh, which does not exist in the
            ;; Guix build sandbox (build fails after the full compile). Resolve
            ;; sh on PATH instead. No-op for versions (e.g. 4.10.0) that dropped
            ;; the step — substitute* leaves a non-matching file untouched.
            (substitute* "src/CMakeLists.txt"
              (("COMMAND /bin/sh") "COMMAND sh"))
            ;; 4.5.0 searches for the auxiliary engine pk3s (lights, brightmaps,
            ;; widescreen gfx) ONLY in the config's search dirs, so a stale
            ;; ~/.config/gzdoom ini hides them. 4.10.0 already checks progdir
            ;; first for these — upstream's own robustness fix. Backport it to
            ;; the older engine so, combined with the pk3-into-bin symlinks
            ;; below, discovery is fully ini-independent. No-op on any version
            ;; that already passes `true` (pattern absent → file untouched).
            (substitute* "src/d_main.cpp"
              (("BaseFileSearch \\(\"lights.pk3\", NULL, false")
               "BaseFileSearch (\"lights.pk3\", NULL, true")
              (("BaseFileSearch \\(\"brightmaps.pk3\", NULL, false")
               "BaseFileSearch (\"brightmaps.pk3\", NULL, true")
              (("BaseFileSearch \\(\"game_widescreen_gfx.pk3\", NULL, false")
               "BaseFileSearch (\"game_widescreen_gfx.pk3\", NULL, true"))))))
    (arguments
     (substitute-keyword-arguments (package-arguments uzdoom)
       ((#:phases phases)
        #~(modify-phases #$phases
            ;; Namespace the outputs so pinned versions coexist in one profile.
            (add-after 'install 'namespace-outputs
              (lambda _
                (rename-file (string-append #$output "/bin/gzdoom")
                             (string-append #$output "/bin/gzdoom-" #$version))
                (rename-file (string-append #$output "/share/games/doom")
                             (string-append #$output "/share/games/gzdoom-" #$version))
                ;; Symlink every engine pk3 into bin/ (progdir). gzdoom locates
                ;; gzdoom.pk3 and the auxiliaries by checking the running
                ;; binary's own directory FIRST (see BaseFileSearch), before any
                ;; ini search path. The real binary lives in bin/, so linking the
                ;; pk3s here makes discovery independent of any home's stale
                ;; gzdoom.ini.
                ;;
                ;; This comment used to end "and progdir resolves to this store
                ;; bin/ via /proc/self/exe even when the wrapper is run from a
                ;; profile". That was false, and it cost every gzdoom port a
                ;; launch: gzdoom derives progdir from *argv[0]*, not
                ;; /proc/self/exe. Proven by running one identical binary two
                ;; ways — same /proc/self/exe, argv[0] a full path vs a bare
                ;; name — where only the bare-name run failed. See the wrapper
                ;; phase below for why that mattered.
                (let ((share (string-append #$output "/share/games/gzdoom-"
                                            #$version)))
                  (with-directory-excursion (string-append #$output "/bin")
                    (for-each
                     (lambda (pk3)
                       (symlink (string-append "../share/games/gzdoom-"
                                               #$version "/" (basename pk3))
                                (basename pk3)))
                     (find-files share "\\.pk3$"))))))
            (replace 'wrap-uzdoom
              (lambda _
                (let ((exe (string-append #$output "/bin/gzdoom-" #$version)))
                  (wrap-program exe
                    `("GUIX_GZDOOM_PREFIX" = (,#$output)))
                  ;; wrap-program emits `exec -a "${0##*/}" <real> "$@"`, which
                  ;; hands the engine a bare basename as argv[0]. gzdoom derives
                  ;; progdir from argv[0], so with no directory component it
                  ;; could not see the pk3s symlinked beside the real binary
                  ;; directly above, and every launch died with "Cannot find
                  ;; gzdoom.pk3" — through the Ports menu, through Lutris, and
                  ;; from a bare shell alike. The engines built and installed
                  ;; fine, which is exactly why this survived an artifact-level
                  ;; review: a green build proves the thing was built, never
                  ;; that it runs.
                  ;;
                  ;; Dropping -a restores a path-bearing argv[0] (the real
                  ;; binary's own store path), so progdir lands in this store
                  ;; bin/ no matter how the engine was invoked — including via
                  ;; the room-gaming profile symlink, whose own bin/ cannot
                  ;; carry the pk3s because 4.10.0 and 4.5.0 would collide on
                  ;; identical filenames in the union.
                  (substitute* exe
                    (("exec -a \"\\$\\{0##\\*/\\}\" ") "exec ")))))))))
    (inputs (modify-inputs (package-inputs uzdoom) (prepend mesa)))
    (synopsis (string-append "GZDoom " version
                             " (version-exact, pinned mod contracts)"))))

;; Load-bearing pins (frequency from the ports scripts, 2026-07-23).
(define gzdoom-4.10.0
  (make-gzdoom "4.10.0"
               "081ssajrb5xnyk35ngc15sad12qd4wmchsjwfr5gv3840ln540l7"))
(define gzdoom-4.5.0
  (make-gzdoom "4.5.0"
               "07b1csbgh5ai81zad1fsnj74yifmwd5mhhzj55n2llxf3li1msr1"))

;; gzdoom-engines: union of the pinned engines into ONE profile entry.
;; Guix dedupes a profile by package `name`, so two packages both named
;; "gzdoom" cannot coexist even though their outputs are namespaced. Rather
;; than version the package name (which changes the derivation and forces a
;; full recompile of already-built, verified engines), we symlink each engine's
;; absolute wrapper into a single trivial output. The wrappers are fully
;; self-referential (they hardcode GUIX_GZDOOM_PREFIX to their own store path
;; and exec their absolute real binary), so a bare symlink resolves the pk3 and
;; runs correctly from any profile. Only the public bin/gzdoom-<v> wrappers are
;; linked — the hidden .gzdoom-<v>-real binaries stay behind their wrappers.
(define gzdoom-engines
  (package
    (name "gzdoom-engines")
    (version "1.0")
    (source #f)
    (build-system trivial-build-system)
    (arguments
     (list
      #:modules '((guix build utils))
      #:builder
      #~(begin
          (use-modules (guix build utils))
          (let ((bin (string-append #$output "/bin")))
            (mkdir-p bin)
            (for-each
             (lambda (engine)
               (for-each
                (lambda (wrapper)
                  (let ((base (basename wrapper)))
                    (when (string-prefix? "gzdoom-" base)
                      (symlink wrapper (string-append bin "/" base)))))
                (find-files (string-append engine "/bin") #:directories? #f)))
             (list #$gzdoom-4.10.0 #$gzdoom-4.5.0))))))
    (synopsis "Pinned GZDoom engines (version-exact mod contracts) as one profile entry")
    (description "Symlinks the version-namespaced GZDoom wrappers (gzdoom-4.10.0,
gzdoom-4.5.0) into a single profile so the ports engine resolver and Lutris both
find every pinned engine under one bin/ directory.")
    (home-page (package-home-page gzdoom-4.10.0))
    (license (package-license gzdoom-4.10.0))))

;; --- 3D Teapot — the authentic BeOS GLTeapot, Linux-native -----------------
;; The literal Newell/Utah teapot, lit and spinning, via freeglut's built-in
;; glutSolidTeapot.  No prebuilt teapot exists in Guix (mesa-demos is
;; unpackaged), so this is the ~40-line GLUT program promised in the demos
;; contract (2026-07-23), compiled in-profile against freeglut + GLU + mesa.
;; Press q or Escape to quit.  Mètsàtron 2026-07-24.
(define redstone-glteapot
  (package
    (name "redstone-glteapot")
    (version "1.0")
    (source
     (plain-file "glteapot.c" "\
#include <GL/freeglut.h>
#include <GL/glu.h>
static float a = 0.f;
static void disp(void){
  glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
  glLoadIdentity(); gluLookAt(0,0,6, 0,0,0, 0,1,0);
  glRotatef(20,1,0,0); glRotatef(a,0,1,0);
  { GLfloat d[]={0.62f,0.64f,0.70f,1.f}; glMaterialfv(GL_FRONT,GL_DIFFUSE,d); }
  glutSolidTeapot(1.6); glutSwapBuffers();
}
static void idle(void){ a+=0.4f; if(a>360)a-=360; glutPostRedisplay(); }
static void resh(int w,int h){
  glViewport(0,0,w,h); glMatrixMode(GL_PROJECTION); glLoadIdentity();
  gluPerspective(40.0,(double)w/(h?h:1),1.0,20.0); glMatrixMode(GL_MODELVIEW);
}
static void key(unsigned char k,int x,int y){ (void)x;(void)y;
  if(k==27||k=='q') glutLeaveMainLoop(); }
int main(int argc,char**argv){
  glutInit(&argc,argv);
  glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH);
  glutInitWindowSize(520,440); glutCreateWindow(\"GLTeapot\");
  glClearColor(0,0,0,1);
  glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING);
  glEnable(GL_LIGHT0); glEnable(GL_NORMALIZE);
  { GLfloat lp[]={2,2,3,0}, ld[]={0.95f,0.9f,0.75f,1},
           la[]={0.2f,0.2f,0.22f,1}, ms[]={1,1,1,1};
    glLightfv(GL_LIGHT0,GL_POSITION,lp); glLightfv(GL_LIGHT0,GL_DIFFUSE,ld);
    glLightfv(GL_LIGHT0,GL_AMBIENT,la); glMaterialfv(GL_FRONT,GL_SPECULAR,ms);
    glMaterialf(GL_FRONT,GL_SHININESS,64.f); }
  glutDisplayFunc(disp); glutReshapeFunc(resh);
  glutIdleFunc(idle); glutKeyboardFunc(key);
  glutMainLoop(); return 0;
}
"))
    (build-system gnu-build-system)
    (arguments
     (list
      #:tests? #f
      #:phases
      #~(modify-phases %standard-phases
          (delete 'configure)
          (replace 'unpack
            (lambda* (#:key source #:allow-other-keys)
              (copy-file source "glteapot.c")))
          (replace 'build
            (lambda _
              (invoke "gcc" "glteapot.c" "-O2" "-o" "redstone-glteapot"
                      "-lglut" "-lGLU" "-lGL" "-lm")))
          (replace 'install
            (lambda* (#:key outputs #:allow-other-keys)
              (install-file "redstone-glteapot"
                            (string-append (assoc-ref outputs "out")
                                           "/bin")))))))
    (inputs (list freeglut glu mesa))
    (home-page "https://en.wikipedia.org/wiki/Utah_teapot")
    (synopsis "Spinning Utah teapot — Linux-native BeOS GLTeapot stand-in")
    (description "A minimal freeglut program that renders the lit, rotating
Newell/Utah teapot: the Linux-native counterpart to BeOS's iconic GLTeapot
demo.  Press q or Escape to quit.")
    (license license:x11)))

(packages->manifest
 (cons* pcmanfm-redstone
        xosd-redstone   ; desktop-layer osd_cat for the Redstone build stamp
        icewm-gradients  ; replaces "icewm" spec — gradient-capable build
        icewm-control-panel ; IceWMCP 3.2 and its complete bundled applet suite
        netactview       ; IceWM taskbar Net meter's NetStatusCommand target
        gzdoom-engines   ; union of the pinned engines (4.10.0 + 4.5.0) as one entry
        redstone-glteapot ; authentic spinning Utah teapot (BeOS GLTeapot, in-profile GLUT build)
        (map specification->package
             '(
   "rofi"     ; Windows-95 Run/launcher dialogs (stock rofi, fixed-geometry theme)
   "clipmenu" "clipnotify" "xsel" ; clipboard history and X11 clipboard backend
   "gtk+"     ; GTK schemas, including org.gtk.Settings.FileChooser
   "pluma"    ; MATE text editor for Redstone native apps
   "audacious" ; Winamp-skin-capable audio player
   "pnmixer"  ; lightweight system tray volume applet
   "network-manager-applet" ; tray applet; launched only when NetworkManager is active
   "lxappearance" ; GTK theme/icon settings UI
   "dbus"     ; dbus-run-session wraps icewm-session for GLib/GIO apps
   "gsettings-desktop-schemas" ; schemas required by PCManFM desktop preferences
   "xrdb"     ; load Redstone URxVT Xresources into Xephyr
   "xterm"    ; fallback terminal
   "xdpyinfo"  ; display info
   "xwininfo"  ; window inspection
   "xprop"     ; window/root properties
   "xrandr"    ; display DPI configuration
   ;; --- Redstone 9X accessory + game suite ---
   "mousepad"    ; XFCE text editor — Redstone 9X default text editor
   "gpaint"      ; GNU Paint — MS Paint-style raster editor (Accessories)
   "abiword"     ; AbiWord — word processor, the WordPad/Word stand-in (Accessories)
   "gnumeric"    ; Gnumeric — spreadsheet, the Excel/Works stand-in (Accessories)
   "zeal"        ; Zeal — offline documentation browser, the Start-menu "Help"
   "fsearch"     ; FSearch — fast file search, the Start-menu "Find"
   "xfe"         ; X File Explorer — FOX-toolkit Explorer-style file manager (Start-menu "Xfe"; the entry existed with no package behind it until 2026-07-18)
   "gimp"        ; GNU Image Manipulation Program (Accessories)
   "inkscape"    ; SVG/vector graphics editor (Accessories)
   "libreoffice" ; LibreOffice suite (Accessories) — the real Office next to the AbiWord/Gnumeric stand-ins
   ;; --- MATE + FOX additions (Mètsàtron 2026-07-19) ---
   "pluma"       ; MATE text editor (Accessories)
   "geany"       ; lightweight IDE (Development)
   "eom"         ; Eye of MATE image viewer (Graphics)
   "mate-system-monitor" ; launched by the taskbar CPU meter (SerenityOS scheme)
   "fox"         ; FOX toolkit 1.6 — build/customise FOX apps in-room (ships adie, PathFinder)
   "pavucontrol" ; PulseAudio volume control — pnmixer's VolumeControlCommand target
   "lxtask"      ; maintained backend for IceWMCP's historical Processes applet
   "xscreensaver" ; backend and configuration UI for IceWMCP's Screen Saver applet
   "lxinput"     ; ice2k Control Panel Mouse/Keyboard applet backend (control calls `lxinput`)
   "jstest-gtk"  ; ice2k Control Panel Game Controllers applet backend (control calls `jstest-gtk`)
   "xlockmore"   ; provides `xlock` — backend for ice2k Display applet's Screen Saver tab (desk.cpp parses `xlock` modes for the list and previews via `xlock -mode X -nolock`); ice2k intentionally does not vendor-build it since Guix packages it
   "uzdoom"      ; GZDoom continuation fork (community lineage, Guix main = rung 1) — in-sanctuary engine for the gzdoom/* ports scripts + Lutris ports-bridge; the x230-built gzdoom bundles in the RetroPie tree are FHS binaries (INTERP /lib64/ld-linux) the Guix guest cannot exec, so the bridge substitutes this engine for `./bin/gzdoom-*/gzdoom` (sealed 2026-07-23)
   "xarchiver"   ; GTK archive manager (Accessories) — replaced Ark; GTK themes cleanly under the sanctuary GTK theme, no KF6/kdeglobals colour-scheme gap, no CSD headerbar
   ;; --- KDE game suite (Mètsàtron 2026-07-25) ---
   ;; These are KF6 apps, so the Ark caveat one line above was expected to bite:
   ;; KF6 takes its palette from KColorScheme/kdeglobals rather than qt6ct, so
   ;; the prediction was that they would ignore the active Desktop Scheme. That
   ;; prediction was WRONG — tested live against the Windows and CDE schemes and
   ;; they conform. The qt6ct/Kvantum stack reaches further than the Ark note
   ;; implies, at least for these three. No kdeglobals generator is needed; if a
   ;; future scheme does diverge, that is the lever to reach for.
   "kmahjongg"   ; KMahjongg — tile-matching solitaire
   "kshisen"     ; KShisen — Shisen-Sho, the KMahjongg variant
   "kpat"        ; KPatience — card solitaire collection (binary is `kpat`)
   ;; Board / logic
   "kreversi"    ; KReversi — Reversi/Othello, the game Windows 1.0 shipped with
   "bovo"        ; Bovo — five-in-a-row (Gomoku)
   "kfourinline" ; KFourInLine — Connect Four
   "ksquares"    ; KSquares — dots and boxes
   "knights"     ; KNights — chess front-end
   "kigo"        ; Kigo — Go, against the GnuGo engine
   "kajongg"     ; Kajongg — four-player Mah Jongg (the real tile game, not solitaire)
   "lskat"       ; LSkat — Lieutenant Skat, two-player card game
   "kiriki"      ; Kiriki — Yahtzee-style dice
   ;; Puzzle
   "katomic"     ; KAtomic — Sokoban-like molecule assembly
   "skladnik"    ; Skladnik — Sokoban (this IS the renamed ksokoban; that name is retired)
   "klines"      ; Kolor Lines — colour-line elimination
   "kmines"      ; KMines — KDE's Minesweeper
   "picmi"       ; Picmi — nonogram / picross
   "kblocks"     ; KBlocks — falling-block puzzler
   ;; Arcade / action
   "kbounce"     ; KBounce — Jezzball
   "kbreakout"   ; KBreakOut — Breakout
   "kapman"      ; Kapman — Pac-Man
   "kgoldrunner" ; KGoldrunner — Lode Runner
   "ksnakeduel"  ; KSnakeDuel — Tron light-cycles
   "granatier"   ; Granatier — Bomberman
   "kolf"        ; Kolf — minigolf
   ;; --- KF6 runtime deps of the KNewStuff "Get New ..." dialogs ---
   ;; KNS ships its dialog QML compiled into each binary (qrc:/qt/qml/org/kde/
   ;; newstuff/), but that QML imports modules no game pulls in itself. They
   ;; surface one at a time as each import is satisfied: kirigami first
   ;; (DialogContent.qml:10), then kcmutils (Page.qml:12) once kirigami
   ;; resolved. Both are QML-only deps — see @ROOM_QT6_QML@ in the menu, because
   ;; installing them is NOT enough: room-gaming's etc/profile exports no QML
   ;; import path, so the modules stay invisible to Qt without it.
   "kirigami"    ; org.kde.kirigami  — KNS DialogContent.qml
   "kcmutils"    ; org.kde.kcmutils  — KNS Page.qml
   "vscodium"    ; VSCodium (nonguix channel) — community telemetry-free VSCode build; binary is `codium`
   "smplayer"    ; SMPlayer — Qt front-end for mpv/mplayer (Multimedia)
   "atril"       ; Atril — MATE document viewer, PDF/PostScript (Accessories)
   "qt6ct"       ; Qt6 config tool — drives the built-in "Windows" style + Win95 palette for Zeal, which is a Qt6 app (qtbase-6.9.2), NOT Qt5 — so qt5ct would be inert here. Co-located with Zeal so the qt6ct platformtheme plugin (lib/qt6/plugins/platformthemes/libqt6ct.so) resolves; env-inert in the profile so it never touches session start — QT_QPA_PLATFORMTHEME=qt6ct is set per-app on the menu entries, not in the session command.
   "kvantum"     ; Qt5/Qt6 SVG theme engine — CDE dynasty schemes set QT_STYLE="kvantum" (qt6ct's style= key) because CDE's Motif look has no equivalent among qt6ct's built-in styles; the Commonality theme family (linux/.config/Kvantum/) supplies the actual Kvantum SVG theme.
   "tcalc"       ; terminal calculator — legacy fvwm95 spin only; Accessories switched to mate-calc
   "mate-calc"   ; MATE calculator (Accessories) — the actual GUI calculator, replaces xcalc; matches the room's Pluma/Eye of MATE/Atril MATE-app theming
   "aisleriot"   ; Solitaire card games: Klondike (default) and FreeCell (--variation=freecell)
   "sdl2"         ; SDL2 runtime — dsdmine (Minesweeper) links against it
   "gnubg"       ; GNU Backgammon (Games)
   "freeciv"     ; FreeCiv turn-based strategy (Games) — client: freeciv-gtk3
   "corsix-th"   ; CorsixTH — open-source Theme Hospital clone (Games)
   "openttd"     ; OpenTTD — Transport Tycoon Deluxe clone (Games)
   "openrct2"    ; OpenRCT2 — RollerCoaster Tycoon 2 clone (Games)

   ;; --- Console emulators for the Redstone desktop (2026-07-15) --------------
   ;; Rebuilding the childhood, period-correct.  Guix main = rung 1.
   "zsnes"                   ; SNES — github.com/xyproto/zsnes, the MAINTAINED fork.
                             ; Upstream ZSNES died at 1.51; Guix ships the fork at 2.0.12
                             ; (verified: the package's own git url IS xyproto/zsnes).
   "mupen64plus-ui-console"  ; N64 — mupen64plus, console front-end

   ;; --- BeOS-style Demos suite (Mètsàtron 2026-07-23, contract sealed) --------
   ;; The authentic BeOS GLTeapot / Mandelbrot / Kaleidoscope / 3dmov binaries
   ;; are x86 BeOS ELF and belong to the future BeOS/Haiku enclave — these are
   ;; the real Linux-native stand-ins, no approximations, all Guix main = rung 1.
   "xaos"        ; Mandelbrot — real-time interactive fractal zoomer
   "golly"       ; Game of Life — Conway/Gosper cellular-automaton explorer
   "glmark2"     ; the famous OpenGL scenes reel — stands in for the spinning
                 ; Utah teapot until a packaged GLUT teapot demo lands (see below)
   "mesa-utils"  ; provides glxgears — the classic GL gears demo
   ;; Kaleidoscope is already covered by "xscreensaver" above (kaleidescope hack).
   ;; TODO(teapot): no standalone Guix package for a literal spinning Utah teapot
   ;; (mesa-demos isn't packaged). Authentic touch = a ~40-line GLUT program in
   ;; local-packages/; glmark2 covers "famous GL scenes" in the meantime.
   ))))
;; room-gaming:1 ends here
