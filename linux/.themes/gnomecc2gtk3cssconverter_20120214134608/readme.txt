gnomecc 2 gtk3css converter
Paulo Silva - feb 2012 - gpl license



This is more a colour scheme converter than a theme properly - the theme part is based on Zukitwo (the default one were cleaned to look more like Motif from 4dwm/irix/sgi ), and it were edited to accept conversions from config.xml from ~/.gnome-color-chooser folder.

For using this theme/converter conviniently, gnome-color-chooser (available defaultly from Debian and Ubuntu repositories) needs to be installed.



in this folder there is some 3 'hidden' ('.*') folders inside (push 'ctrl+h' keys for seeing them on Nautilus):
- .config/gtk-3.0
- .gnome-color-chooser
- .themes

the files from '.themes' are to be copied to '.themes' - it only has a Metacity window decoration theme fully compatible with gnome-color-chooser, MistRB.

the files from '.config/gtk-3.0' are to be copied to '~/.config/gtk-3.0' - all files found there (like 'gtk.css') are to be renamed as backup, for avoiding file replacement.

the files from '.gnome-color-chooser' are to be copied to '~/.gnome-color-chooser' - all files found there (like 'config.xml') are to be renamed as backup - gnome-color-chooser will open defaultly the existing config.xml file when running, and config.css will be assumed (as css include) from this gtk3 theme.



with the terminal located at '~/.gnome-color-chooser', the command 'bash gnomecc2gtk3css.sh' will convert config.xml to config.css - the file config.xml is updated everytime the Apply button from gnome-color-chooser is clicked, and config.css is the colour scheme loaded from this gtk3 theme.



I never used gnome-tweak-tool successfully, but this colour scheme hack for gtk3 seems to work perfectly fine (since i always loved gnome-color-chooser, and i miss it a lot on gtk3).

This needs huge improvements for a more comfortable use. Be welcome on fixing and improving it. Thanks!



