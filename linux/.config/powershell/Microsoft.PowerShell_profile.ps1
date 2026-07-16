# Redstone 9X — Windows PowerShell profile
# Projected from DotCortex: sanctuary-distrobox.org

# Distinguish from native pwsh in prompt colour
function Prompt {
    $host.UI.RawUI.WindowTitle = "Windows PowerShell"
    "PS $($PWD.Path)> "
}

# Make bash easily reachable from pwsh
function bash { /usr/bin/env bash @args }
