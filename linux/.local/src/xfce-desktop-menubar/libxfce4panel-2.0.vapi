[CCode (cheader_filename = "libxfce4panel/libxfce4panel.h")]
namespace Xfce {
	[CCode (type_id = "xfce_panel_plugin_get_type ()", cname = "XfcePanelPlugin")]
	public class PanelPlugin : Gtk.EventBox {
		[CCode (has_construct_function = false)]
		protected PanelPlugin ();
		public unowned string get_name ();
		public int get_size ();
		public Gtk.Orientation get_orientation ();
		public void set_expand (bool expand);
		public void set_small (bool small);
		public signal void orientation_changed (Gtk.Orientation orientation);
		public signal void size_changed (int size);
	}
}
