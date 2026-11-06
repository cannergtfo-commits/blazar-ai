# Blazar AI job runner — manual only. Drains queue\ then exits and unloads the model.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Test-Path ".\paused.flag") {
  Write-Host "paused.flag is set — remove it to run."
  exit 1
}
$py = "C:\Users\canne\AppData\Local\Programs\Python\Python312\python.exe"
& $py "$PSScriptRoot\runner.py" @args
$rc = $LASTEXITCODE
Write-Host ""
Write-Host "Done. Exit code $rc. Model unload is handled by the runner."
exit $rc
