# choco-bootstrap.ps1 — install Chocolatey if not present
# Requires admin and outbound HTTPS

if (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Host "Chocolatey already installed: $(choco --version)"
    exit 0
}

Write-Host "Installing Chocolatey..."
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
Write-Host "Chocolatey installed: $(choco --version)"
