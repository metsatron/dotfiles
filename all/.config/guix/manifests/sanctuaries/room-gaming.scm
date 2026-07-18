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
(use-modules (guix packages)
             (guix gexp)
             (guix utils)
             (gnu packages lxde)
             (gnu packages xdisorg))

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

(packages->manifest
 (cons* pcmanfm-redstone
        (map specification->package
             '(
   "icewm"    ; Win9x/XP-era WM — Windows-95 theme
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
   "vscodium"    ; VSCodium (nonguix channel) — community telemetry-free VSCode build; binary is `codium`
   "smplayer"    ; SMPlayer — Qt front-end for mpv/mplayer (Multimedia)
   "atril"       ; Atril — MATE document viewer, PDF/PostScript (Accessories)
   "qt6ct"       ; Qt6 config tool — drives the built-in "Windows" style + Win95 palette for Zeal, which is a Qt6 app (qtbase-6.9.2), NOT Qt5 — so qt5ct would be inert here. Co-located with Zeal so the qt6ct platformtheme plugin (lib/qt6/plugins/platformthemes/libqt6ct.so) resolves; env-inert in the profile so it never touches session start — QT_QPA_PLATFORMTHEME=qt6ct is set per-app on the menu entries, not in the session command.
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
