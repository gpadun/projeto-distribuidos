param(
    [string]$IdRestaurante = "restaurante-1",
    [string]$AdmUrl = "",
    [switch]$SemPreparoAuto
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

Write-Host "Restaurante $IdRestaurante ouvindo PedidoDisponivel"
Write-Host "ADM lider: $AdmUrl"

$argsList = @(
    "-m", "src.clients.mock_restaurant",
    "--id-restaurante", $IdRestaurante,
    "--adm-url", $AdmUrl
)

if ($SemPreparoAuto) {
    $argsList += "--sem-preparo-auto"
}

& "$projectRoot\.venv\Scripts\python.exe" @argsList
