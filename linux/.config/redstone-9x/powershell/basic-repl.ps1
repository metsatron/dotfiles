$host.UI.RawUI.WindowTitle = "Windows PowerShell"
Remove-Module PSReadLine -Force -ErrorAction SilentlyContinue

while ($true) {
    [Console]::Write("PS $($PWD.Path)> ")
    $line = [Console]::ReadLine()
    if ($null -eq $line) { break }
    if ($line.Trim() -eq "exit") { break }
    if ($line.Trim().Length -eq 0) { continue }

    try {
        Invoke-Expression $line
    }
    catch {
        Write-Error $_
    }
}
