param(
    [string]$IdEntregador = "entregador-1",
    [string]$AdmUrl = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

. (Join-Path $PSScriptRoot "resolve_adm_lider.ps1")
$AdmUrl = Resolve-AdmLiderUrl -AdmUrl $AdmUrl

$env:RABBITMQ_ENABLED = "1"
$env:RABBITMQ_HOST = "127.0.0.1"
$env:RABBITMQ_PORT = "5672"
$env:RABBITMQ_USER = "dsid"
$env:RABBITMQ_PASSWORD = "dsid123"
$env:ADM_URL = $AdmUrl
$env:ADM_URLS = "http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003"

Write-Host "Entregador $IdEntregador ouvindo PedidoDisponivel"
Write-Host "ADM lider: $AdmUrl"

& "$projectRoot\.venv\Scripts\python.exe" @(
    "-m", "src.clients.mock_driver",
    "--modo", "broker",
    "--id-entregador", $IdEntregador,
    "--adm-url", $AdmUrl
)
