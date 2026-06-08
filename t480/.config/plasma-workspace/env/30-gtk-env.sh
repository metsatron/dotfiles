# SonicDE GTK environment — appmenu bridge and CSD suppression.
# Plasma env scripts run before the session shell, runner, and menu services.
export GTK_CSD=0
export GTK3_NOCSD=1
# appmenu-gtk-module bridges GTK3 apps into KDE/SonicDE global menu via D-Bus.
export GTK_MODULES=appmenu-gtk-module
export UBUNTU_MENUPROXY=1
