# windows-install.ps1 — full Windows fleet provisioning
# Run as admin from the deployed win/.windows/bin/ directory

$here = $PSScriptRoot

Write-Host "=== Windows Fleet Install ===" -ForegroundColor Cyan

# 1 — PowerShell profile
Write-Host "`n[1/4] PowerShell profile..." -ForegroundColor Yellow
$profileDir = Split-Path $PROFILE
New-Item -ItemType Directory -Force $profileDir | Out-Null
Copy-Item "$here\..\..\config\powershell\Microsoft.PowerShell_profile.ps1" $PROFILE -Force
Write-Host "  Profile deployed to $PROFILE"

# 2 — OpenSSH default shell → pwsh
Write-Host "`n[2/4] Setting pwsh as OpenSSH default shell..." -ForegroundColor Yellow
$pwsh = "$env:ProgramFiles\PowerShell\7\pwsh.exe"
if (Test-Path $pwsh) {
    reg add "HKLM\SOFTWARE\OpenSSH" /v DefaultShell /t REG_SZ /d $pwsh /f | Out-Null
    reg add "HKLM\SOFTWARE\OpenSSH" /v DefaultShellCommandOption /t REG_SZ /d "/c" /f | Out-Null
    Write-Host "  DefaultShell set to $pwsh"
} else {
    Write-Warning "  pwsh not found at $pwsh — skipping"
}

# 3 — Winget packages
Write-Host "`n[3/4] Winget packages..." -ForegroundColor Yellow
& "$here\winget-apply.ps1"

# 4 — Chocolatey
Write-Host "`n[4/4] Chocolatey..." -ForegroundColor Yellow
& "$here\choco-bootstrap.ps1"
& "$here\choco-apply.ps1"

Write-Host "`n=== Done ===" -ForegroundColor Cyan
