# Minimal vi/vim shims (prefer Guix nvim)
if command -v nvim >/dev/null 2>&1; then
  alias vi='nvim'
  alias vim='nvim'
fi
