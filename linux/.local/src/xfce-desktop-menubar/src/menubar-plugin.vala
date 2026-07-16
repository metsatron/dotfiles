/*
 * xfce-desktop-menubar — DotCortex native libxfce4panel plugin.
 *
 * Fallback global-menu bar for XFCE. Renders File/Edit/Go/Recent/Windows/Help
 * and hides itself whenever the active window already exports an application
 * menu, interlocking with xfce4-appmenu-plugin exactly as
 * org.dotcortex.desktopmenu interlocks with the KDE Global Menu on SonicDE.
 *
 * Tangled from desktop-xfce.org — never edit under the overlay.
 */

namespace DesktopMenubar {

    public class Plugin : Xfce.PanelPlugin {

        Gtk.MenuBar menubar;
        unowned Wnck.Screen screen;
        string brand;
        uint recheck_id = 0;

        construct {
            brand = load_brand ();

            menubar = new Gtk.MenuBar ();
            menubar.set_pack_direction (Gtk.PackDirection.LTR);

            build_menus ();
            apply_style ();

            add (menubar);
            menubar.show_all ();

            orientation_changed.connect ((o) => {
                menubar.set_pack_direction (o == Gtk.Orientation.HORIZONTAL
                    ? Gtk.PackDirection.LTR : Gtk.PackDirection.TTB);
            });

            screen = Wnck.Screen.get_default ();
            screen.force_update ();
            screen.active_window_changed.connect (on_active_window_changed);

            update_visibility ();
        }

        /* ---- brand string (configurable, neutral default — never "SonicDE") ---- */
        string load_brand () {
            var path = Path.build_filename (Environment.get_user_config_dir (),
                                            "xfce-desktop-menubar", "brand");
            if (FileUtils.test (path, FileTest.EXISTS)) {
                try {
                    string c;
                    FileUtils.get_contents (path, out c);
                    c = c.strip ();
                    if (c != "")
                        return c;
                } catch (Error e) { /* fall through */ }
            }
            return Environment.get_host_name ();
        }

        // Let the panel background show through, and keep only the brand bold
        // (the brand label carries its own Pango bold markup, which wins over
        // this normal-weight rule). Scoped to this plugin's own wrapper process.
        void apply_style () {
            var css = new Gtk.CssProvider ();
            try {
                css.load_from_data (
                    "menubar, menubar > menuitem { background-color: transparent; background-image: none; box-shadow: none; border-width: 0; }\n" +
                    "menubar > menuitem > label { font-weight: normal; }");
            } catch (Error e) {
                warning ("xfce-desktop-menubar: css load failed: %s", e.message);
                return;
            }
            Gtk.StyleContext.add_provider_for_screen (
                Gdk.Screen.get_default (), css,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION);
        }

        void launch (string cmdline) {
            try {
                Process.spawn_command_line_async (cmdline);
            } catch (Error e) {
                warning ("xfce-desktop-menubar: spawn failed: %s", e.message);
            }
        }

        void add_action (Gtk.Menu menu, string label, owned string cmd) {
            var it = new Gtk.MenuItem.with_label (label);
            it.activate.connect (() => launch (cmd));
            menu.append (it);
        }

        void add_sep (Gtk.Menu menu) {
            menu.append (new Gtk.SeparatorMenuItem ());
        }

        Gtk.MenuItem top_item (string label, Gtk.Menu submenu) {
            var it = new Gtk.MenuItem.with_label (label);
            it.set_submenu (submenu);
            return it;
        }

        /* ------------------------------ menus ------------------------------ */
        void build_menus () {
            // Brand (Apple-style) menu.
            var brand_menu = new Gtk.Menu ();
            add_action (brand_menu, "About This Computer",
                "sh -c " + Shell.quote ("zenity --info --no-wrap --title='About This Computer' --text=\"$(. /etc/os-release 2>/dev/null; echo \"$PRETTY_NAME\"; uname -sr; echo \"Host: $(uname -n)\"; echo \"Memory: $(free -h | awk '/^Mem:/{print $2}')\")\""));
            add_action (brand_menu, "Settings Manager…", "xfce4-settings-manager");
            add_sep (brand_menu);
            add_action (brand_menu, "Lock Screen", "xflock4");
            add_action (brand_menu, "Log Out…", "xfce4-session-logout");
            var brand_item = new Gtk.MenuItem ();
            var brand_lbl = new Gtk.Label (null);
            brand_lbl.set_markup ("<b>" + Markup.escape_text (brand) + "</b>");
            brand_item.add (brand_lbl);
            brand_item.set_submenu (brand_menu);

            // File.
            var file_menu = new Gtk.Menu ();
            add_action (file_menu, "New File Manager Window", "thunar");
            add_action (file_menu, "New Folder on Desktop…",
                "sh -c " + Shell.quote ("d=\"$(xdg-user-dir DESKTOP 2>/dev/null || echo \"$HOME/Desktop\")\"; n=$(zenity --entry --title='New Folder' --text='Folder name:' --entry-text='New Folder') && [ -n \"$n\" ] && mkdir -p \"$d/$n\""));
            add_action (file_menu, "Open Desktop Folder",
                "sh -c " + Shell.quote ("xdg-open \"$(xdg-user-dir DESKTOP 2>/dev/null || echo \"$HOME/Desktop\")\""));
            add_sep (file_menu);
            add_action (file_menu, "Open Terminal Here", "xfce4-terminal");
            add_sep (file_menu);
            add_action (file_menu, "Open Trash", "thunar trash:///");

            // Edit (settings-oriented, XFCE-native).
            var edit_menu = new Gtk.Menu ();
            add_action (edit_menu, "Desktop & Wallpaper", "xfdesktop-settings");
            add_action (edit_menu, "Appearance", "xfce4-appearance-settings");
            add_action (edit_menu, "Display", "xfce4-display-settings");
            add_sep (edit_menu);
            add_action (edit_menu, "Panel Preferences", "xfce4-panel --preferences");

            // Go (dynamic: XDG dirs + gtk bookmarks).
            var go_menu = new Gtk.Menu ();
            go_menu.show.connect (() => populate_go (go_menu));

            // Recent (self-populating).
            var recent = new Gtk.RecentChooserMenu ();
            recent.set_local_only (false);
            recent.set_show_tips (true);
            recent.set_sort_type (Gtk.RecentSortType.MRU);
            recent.set_limit (15);
            recent.item_activated.connect (() => {
                var uri = recent.get_current_uri ();
                if (uri != null)
                    launch ("xdg-open " + Shell.quote (uri));
            });

            // Windows (dynamic: Wnck task list).
            var windows_menu = new Gtk.Menu ();
            windows_menu.show.connect (() => populate_windows (windows_menu));

            // Help.
            var help_menu = new Gtk.Menu ();
            add_action (help_menu, "About This System",
                "sh -c " + Shell.quote ("zenity --info --no-wrap --title='About This System' --text=\"$(. /etc/os-release 2>/dev/null; echo \"$PRETTY_NAME\"; echo \"$HOME_URL\")\""));
            add_sep (help_menu);
            add_action (help_menu, "XFCE Documentation", "xdg-open https://docs.xfce.org/");
            add_action (help_menu, "About Desktop Menubar",
                "zenity --info --no-wrap --title=Desktop Menubar --text=" + Shell.quote ("DotCortex XFCE Desktop Menubar 0.1.0 — global-menu fallback for XFCE. Tangled from desktop-xfce.org."));

            menubar.append (brand_item);
            menubar.append (top_item ("File", file_menu));
            menubar.append (top_item ("Edit", edit_menu));
            menubar.append (top_item ("Go", go_menu));
            menubar.append (top_item ("Recent", recent));
            menubar.append (top_item ("Windows", windows_menu));
            menubar.append (top_item ("Help", help_menu));
        }

        void populate_go (Gtk.Menu menu) {
            foreach (var c in menu.get_children ())
                menu.remove (c);

            add_go_dir (menu, "Home", Environment.get_home_dir ());
            add_go_special (menu, "Desktop", UserDirectory.DESKTOP);
            add_go_special (menu, "Documents", UserDirectory.DOCUMENTS);
            add_go_special (menu, "Downloads", UserDirectory.DOWNLOAD);
            add_go_special (menu, "Music", UserDirectory.MUSIC);
            add_go_special (menu, "Pictures", UserDirectory.PICTURES);
            add_go_special (menu, "Videos", UserDirectory.VIDEOS);

            var bm = Path.build_filename (Environment.get_user_config_dir (), "gtk-3.0", "bookmarks");
            if (FileUtils.test (bm, FileTest.EXISTS)) {
                try {
                    string content;
                    FileUtils.get_contents (bm, out content);
                    bool sep_added = false;
                    foreach (var raw in content.split ("\n")) {
                        var line = raw.strip ();
                        if (line == "")
                            continue;
                        var parts = line.split (" ", 2);
                        var uri = parts[0];
                        string label = parts.length > 1
                            ? parts[1]
                            : Path.get_basename (uri.replace ("file://", ""));
                        if (!sep_added) { add_sep (menu); sep_added = true; }
                        add_go_uri (menu, label, uri);
                    }
                } catch (Error e) { /* ignore */ }
            }

            add_sep (menu);
            add_action (menu, "Go to Folder…",
                "sh -c " + Shell.quote ("d=$(zenity --file-selection --directory --title='Go to Folder') && [ -n \"$d\" ] && thunar \"$d\""));
        }

        void add_go_dir (Gtk.Menu menu, string label, string? path) {
            if (path == null || !FileUtils.test (path, FileTest.IS_DIR))
                return;
            add_go_uri (menu, label, Filename.to_uri (path, null));
        }

        void add_go_special (Gtk.Menu menu, string label, UserDirectory dir) {
            add_go_dir (menu, label, Environment.get_user_special_dir (dir));
        }

        void add_go_uri (Gtk.Menu menu, string label, string uri) {
            var it = new Gtk.MenuItem.with_label (label);
            it.activate.connect (() => launch ("xdg-open " + Shell.quote (uri)));
            menu.append (it);
            it.show ();
        }

        void populate_windows (Gtk.Menu menu) {
            foreach (var c in menu.get_children ())
                menu.remove (c);
            screen.force_update ();
            bool any = false;
            unowned Wnck.Window active = screen.get_active_window ();
            foreach (unowned Wnck.Window w in screen.get_windows ()) {
                if (w.is_skip_tasklist ())
                    continue;
                any = true;
                var it = new Gtk.CheckMenuItem.with_label (w.get_name ());
                it.draw_as_radio = true;
                it.set_active (w == active);
                unowned Wnck.Window win = w;
                it.activate.connect (() => win.activate (Gtk.get_current_event_time ()));
                menu.append (it);
                it.show ();
            }
            if (!any) {
                var none = new Gtk.MenuItem.with_label ("(no windows)");
                none.sensitive = false;
                menu.append (none);
                none.show ();
            }
        }

        /* ------------------------- interlock (R3) ------------------------- */
        void on_active_window_changed (Wnck.Window? previous) {
            update_visibility ();
            if (recheck_id != 0)
                Source.remove (recheck_id);
            recheck_id = Timeout.add (180, () => {
                recheck_id = 0;
                update_visibility ();
                return Source.REMOVE;
            });
        }

        void update_visibility () {
            unowned Wnck.Window? win = screen.get_active_window ();
            bool available = (win != null) && global_menu_available (win.get_xid ());
            menubar.set_visible (!available);
        }

        bool global_menu_available (ulong xid) {
            if (registrar_has_menu (xid))
                return true;
            if (has_prop (xid, "_GTK_UNIQUE_BUS_NAME")
                && (has_prop (xid, "_GTK_MENUBAR_OBJECT_PATH")
                    || has_prop (xid, "_GTK_APP_MENU_OBJECT_PATH")))
                return true;
            return false;
        }

        bool registrar_has_menu (ulong xid) {
            try {
                var conn = Bus.get_sync (BusType.SESSION);
                var reply = conn.call_sync (
                    "com.canonical.AppMenu.Registrar",
                    "/com/canonical/AppMenu/Registrar",
                    "com.canonical.AppMenu.Registrar",
                    "GetMenuForWindow",
                    new Variant ("(u)", (uint32) xid),
                    new VariantType ("(so)"),
                    DBusCallFlags.NO_AUTO_START, 400, null);
                string service;
                string object_path;
                reply.get ("(so)", out service, out object_path);
                return service != "" && object_path != "" && object_path != "/";
            } catch (Error e) {
                return false;
            }
        }

        // Event-driven read (not a poll): one xprop per active-window transition.
        bool has_prop (ulong xid, string name) {
            string outp;
            int status;
            try {
                Process.spawn_command_line_sync (
                    "xprop -id %lu %s".printf (xid, name), out outp, null, out status);
            } catch (Error e) {
                return false;
            }
            return status == 0 && !outp.contains ("not found") && !outp.contains ("no such");
        }
    }

    // The panel dlopens the .so and calls exactly "xfce_panel_module_init";
    // force the C name so the namespace prefix is not applied.
    [ModuleInit]
    [CCode (cname = "xfce_panel_module_init")]
    public Type xfce_panel_module_init (GLib.TypeModule module) {
        return typeof (DesktopMenubar.Plugin);
    }
}
