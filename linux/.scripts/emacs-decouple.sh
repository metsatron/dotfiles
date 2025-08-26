#!/usr/bin/env bash
set -Eeuo pipefail

stamp="$(date +%Y%m%d-%H%M%S)"
core_src="$HOME/.emacs.d"
core_dst="$HOME/.emacs.d.spacemacs"
vanilla="$HOME/.emacs.d"

if [ -d "$core_src/core" ]; then
  [ ! -e "$core_dst" ] || core_dst="$core_dst.$stamp"
  echo "Moving Spacemacs core:  $core_src -> $core_dst"
  mv -- "$core_src" "$core_dst"
fi

mkdir -p "$vanilla"
[ -f "$vanilla/init.el" ]       || printf ';; vanilla init\n' > "$vanilla/init.el"
[ -f "$vanilla/early-init.el" ] || printf ';; vanilla early-init\n' > "$vanilla/early-init.el"

echo "Done. Plain 'emacs' is vanilla now."
echo "Spacemacs core lives at: $core_dst"
