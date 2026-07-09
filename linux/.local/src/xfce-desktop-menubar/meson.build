project('xfce-desktop-menubar', ['c', 'vala'],
  version: '0.1.0',
  meson_version: '>= 0.56.0',
  default_options: ['warning_level=1'])

add_project_arguments('--vapidir', meson.current_source_dir(), language: 'vala')

glib_dep    = dependency('glib-2.0')
gobject_dep = dependency('gobject-2.0')
gio_dep     = dependency('gio-2.0')
gtk_dep     = dependency('gtk+-3.0')
wnck_dep    = dependency('libwnck-3.0')
panel_dep   = dependency('libxfce4panel-2.0')

plugin_lib_dir  = get_option('libdir') / 'xfce4' / 'panel' / 'plugins'
plugin_data_dir = get_option('datadir') / 'xfce4' / 'panel' / 'plugins'

shared_module('xfce-desktop-menubar',
  sources: 'src/menubar-plugin.vala',
  dependencies: [glib_dep, gobject_dep, gio_dep, gtk_dep, wnck_dep, panel_dep],
  c_args: ['-DWNCK_I_KNOW_THIS_IS_UNSTABLE'],
  vala_args: ['--pkg', 'posix'],
  name_prefix: 'lib',
  install: true,
  install_dir: plugin_lib_dir)

install_data('data/xfce-desktop-menubar.desktop',
  install_dir: plugin_data_dir)
