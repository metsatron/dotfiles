# Plasma/SonicDE sources ~/.config/plasma-workspace/env/*.sh before starting
# the shell, runner, and menu services. Make Guix desktop entries visible there.
if [ -r "$HOME/.xsessionrc.d/20-guix-core-profile.sh" ]; then
  . "$HOME/.xsessionrc.d/20-guix-core-profile.sh"
fi
unset GIO_EXTRA_MODULES
