# wsl-health.ps1: read-only WSL health probe. Starts nothing; `wsl -l -q` only lists distributions.
# A wsl.exe that does not answer within 15 s is reported as WEDGED (the failure seen on 2026-09-17/23).
$ErrorActionPreference = 'SilentlyContinue'
$svc = Get-Service WSLService
"WSLService: $(if ($svc) { $svc.Status } else { 'not installed' })"
$procs = Get-Process wsl, wslhost, wslservice, vmmemWSL
foreach ($g in ($procs | Group-Object ProcessName)) { '{0}: {1} running' -f $g.Name, $g.Count }
$old = $procs | Where-Object { $_.ProcessName -eq 'wsl' -and $_.StartTime -lt (Get-Date).AddHours(-1) }
if ($old) { "STUCK: $(@($old).Count) wsl.exe process(es) older than 1 hour (oldest started $((($old | Sort-Object StartTime)[0]).StartTime.ToString('yyyy-MM-dd HH:mm')))" }
$vm = Get-Process vmmemWSL
if ($vm) { "vmmemWSL up since $($vm.StartTime.ToString('yyyy-MM-dd HH:mm')), $([math]::Round($vm.WorkingSet64 / 1MB)) MB" }
$out = Join-Path $env:TEMP 'wsl-health-probe.txt'
$p = Start-Process -FilePath wsl.exe -ArgumentList '-l', '-q' -NoNewWindow -PassThru -RedirectStandardOutput $out
if ($p.WaitForExit(15000)) {
    $d = @((Get-Content $out -Encoding Unicode) | Where-Object { $_.Trim() })
    "wsl -l -q: answered in time; $($d.Count) distribution(s): $($d -join ', ')"
    'VERDICT: WSL is responsive'
} else {
    Stop-Process -Id $p.Id -Force
    'wsl -l -q: NO ANSWER within 15 s'
    'VERDICT: WSL is WEDGED'
}
Remove-Item $out -Force
