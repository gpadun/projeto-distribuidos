$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $PSScriptRoot "start_adm.ps1"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$startScript`"",
    "-AdmId", "adm-1",
    "-Port", "8001"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$startScript`"",
    "-AdmId", "adm-2",
    "-Port", "8002"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$startScript`"",
    "-AdmId", "adm-3",
    "-Port", "8003"
)

Write-Host "Cluster ADM iniciado:"
Write-Host "  adm-1 -> http://127.0.0.1:8001"
Write-Host "  adm-2 -> http://127.0.0.1:8002"
Write-Host "  adm-3 -> http://127.0.0.1:8003"
Write-Host ""
Write-Host "Aguarde 5-10 segundos para os heartbeats e depois rode:"
Write-Host "  .\scripts\demo_estado.ps1"