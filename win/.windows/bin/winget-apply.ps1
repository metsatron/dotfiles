# winget-apply.ps1 — install manifest packages via winget
# Deploy to target machine and run as admin

$manifest = Join-Path $PSScriptRoot "..\manifest\winget.ssv"
if (-not (Test-Path $manifest)) {
    Write-Error "Manifest not found: $manifest"
    exit 1
}

$winget = "$env:LOCALAPPDATA\Microsoft\WindowsApps\winget.exe"
if (-not (Test-Path $winget)) {
    Write-Error "winget not found"
    exit 1
}

Get-Content $manifest | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '\S' } | ForEach-Object {
    $pkg = ($_ -split '\s+')[0]
    Write-Host "Installing $pkg..."
    & $winget install --id $pkg --accept-source-agreements --accept-package-agreements --silent
}
Write-Host "Done."
