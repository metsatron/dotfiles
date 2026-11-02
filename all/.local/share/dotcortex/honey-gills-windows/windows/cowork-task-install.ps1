# cowork-task-install.ps1: point the CoworkExport scheduled task at the windowless launcher. Idempotent.
# Backs up the task definition first. -WhatIf prints the change and touches nothing. Roll back by importing the
# backup: Register-ScheduledTask -Xml (Get-Content <backup> -Raw) -TaskName CoworkExport -Force
param([switch]$WhatIf)
$ErrorActionPreference = 'Stop'
$task = 'CoworkExport'
$pyw = 'C:\Python314\pythonw.exe'
$dir = Join-Path $env:LOCALAPPDATA 'cowork-export'
$launcher = Join-Path $dir 'run-cowork-export.pyw'
if (-not (Test-Path $launcher)) { throw "launcher missing: $launcher" }
if (-not (Test-Path $pyw)) { throw "pythonw missing: $pyw" }
$t = Get-ScheduledTask -TaskName $task
$a = $t.Actions[0]
if ($a.Execute -eq $pyw -and $a.Arguments -like '*run-cowork-export.pyw*') { 'unchanged: task already runs the windowless launcher'; exit 0 }
$bak = Join-Path $dir ('task-backup-{0}.xml' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
if ($WhatIf) { "would: back up the task to $bak, then run $pyw `"$launcher`" instead of $($a.Execute)"; exit 0 }
Export-ScheduledTask -TaskName $task | Out-File -Encoding utf8 $bak
$new = New-ScheduledTaskAction -Execute $pyw -Argument ('"{0}"' -f $launcher) -WorkingDirectory $dir
Set-ScheduledTask -TaskName $task -Action $new | Out-Null
"installed: task now runs $pyw `"$launcher`" (previous definition saved to $bak)"
