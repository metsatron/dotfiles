# SonicDE GTK environment — appmenu bridge and CSD suppression.
# Plasma env scripts run before the session shell, runner, and menu services.
export GTK_CSD=0
if ldconfig -p 2>/dev/null | grep -q 'libgtk3-nocsd\.so\.0'; then
  export GTK3_NOCSD=1
else
  export GTK3_NOCSD_IGNORE=1
  unset LD_PRELOAD
fi
# appmenu-gtk-module bridges GTK3 apps into KDE/SonicDE global menu via D-Bus.
export GTK_MODULES=appmenu-gtk-module
export UBUNTU_MENUPROXY=1
