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

(packages->manifest
 (cons* pcmanfm-redstone
        xosd-redstone   ; desktop-layer osd_cat for the Redstone build stamp
        icewm-gradients  ; replaces "icewm" spec — gradient-capable build
        icewm-control-panel ; IceWMCP 3.2 and its complete bundled applet suite
        netactview       ; IceWM taskbar Net meter's NetStatusCommand target
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
   "vscodium"    ; VSCodium (nonguix channel) — community telemetry-free VSCode build; binary is `codium`
   "smplayer"    ; SMPlayer — Qt front-end for mpv/mplayer (Multimedia)
   "atril"       ; Atril — MATE document viewer, PDF/PostScript (Accessories)
   "qt6ct"       ; Qt6 config tool — drives the built-in "Windows" style + Win95 palette for Zeal, which is a Qt6 app (qtbase-6.9.2), NOT Qt5 — so qt5ct would be inert here. Co-located with Zeal so the qt6ct platformtheme plugin (lib/qt6/plugins/platformthemes/libqt6ct.so) resolves; env-inert in the profile so it never touches session start — QT_QPA_PLATFORMTHEME=qt6ct is set per-app on the menu entries, not in the session command.
   "kvantum"     ; Qt5/Qt6 SVG theme engine — CDE dynasty schemes set QT_STYLE="kvantum" (qt6ct's style= key) because CDE's Motif look has no equivalent among qt6ct's built-in styles; the Commonality theme family (linux/.config/Kvantum/) supplies the actual Kvantum SVG theme.
   "tcalc"       ; terminal calculator (Accessories) — launched via xterm -e
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
   ))))
;; room-gaming:1 ends here
