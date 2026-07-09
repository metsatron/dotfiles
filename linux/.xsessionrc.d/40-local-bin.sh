#!/usr/bin/env sh
# Put ~/.local/bin on the session PATH so XDG autostart entries can name stowed
# helpers by bare command name. Idempotent: re-sourcing must not duplicate.
case ":${PATH}:" in
  *":$HOME/.local/bin:"*) ;;
  *) PATH="$HOME/.local/bin:$PATH" ;;
esac
export PATH
