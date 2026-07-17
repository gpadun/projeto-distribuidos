param(
    [string]$IdCliente = "cliente-1",
    [string]$IdRestaurante = "restaurante-1",
    [string]$AdmUrl = "",
    [ValidateSet("criar", "rastrear", "demo", "confirmar")]
    [string]$Acao = "demo",
    [string]$IdPedido = ""
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

Write-Host "Cliente $IdCliente acao=$Acao ADM=$AdmUrl"

$argsList = @(
    "-m", "src.clients.mock_customer",
    "--acao", $Acao,
    "--id-cliente", $IdCliente,
    "--id-restaurante", $IdRestaurante,
    "--adm-url", $AdmUrl
)

if ($IdPedido) {
    $argsList += @("--id-pedido", $IdPedido)
}

& "$projectRoot\.venv\Scripts\python.exe" @argsList