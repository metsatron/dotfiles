# choco-apply.ps1 — install manifest packages via Chocolatey

if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Error "Chocolatey not installed. Run choco-bootstrap.ps1 first."
    exit 1
}

$manifest = Join-Path $PSScriptRoot "..\manifest\choco.ssv"
if (-not (Test-Path $manifest)) {
    Write-Error "Manifest not found: $manifest"
    exit 1
}

Get-Content $manifest | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '\S' } | ForEach-Object {
    $pkg = ($_ -split '\s+')[0]
    Write-Host "Installing $pkg..."
    choco install $pkg -y
}
Write-Host "Done."
