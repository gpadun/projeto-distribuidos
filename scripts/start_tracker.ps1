param(
    [string]$IdServidor = "rastreador-1",
    [string]$AdmUrl = "",
    [string]$SupUrl = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

. (Join-Path $PSScriptRoot "resolve_adm_lider.ps1")
$AdmUrl = Resolve-AdmLiderUrl -AdmUrl $AdmUrl

if (-not $SupUrl) {
    $SupUrl = switch ($IdServidor) {
        "rastreador-1" { "http://127.0.0.1:9101" }
        "rastreador-2" { "http://127.0.0.1:9102" }
        default { "" }
    }
}

$env:RABBITMQ_ENABLED = "1"
$env:RABBITMQ_HOST = "127.0.0.1"
$env:RABBITMQ_PORT = "5672"
$env:RABBITMQ_USER = "dsid"
$env:RABBITMQ_PASSWORD = "dsid123"
$env:ADM_URL = $AdmUrl
$env:ADM_URLS = "http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003"
$env:SUP_URL = $SupUrl
$env:TRACKER_HEARTBEAT_INTERVAL = "5"

Write-Host "Subindo rastreador $IdServidor"
Write-Host "ADM_URLS=$env:ADM_URLS SUP=$SupUrl"

& "$projectRoot\.venv\Scripts\python.exe" -c "
from src.clients.tracker_broker import executar_rastreador_broker
executar_rastreador_broker('$IdServidor')
"
