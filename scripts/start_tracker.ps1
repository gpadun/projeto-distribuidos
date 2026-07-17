param(
    [string]$IdServidor = "rastreador-1"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$env:RABBITMQ_ENABLED = "1"
$env:RABBITMQ_HOST = "127.0.0.1"
$env:RABBITMQ_PORT = "5672"
$env:RABBITMQ_USER = "dsid"
$env:RABBITMQ_PASSWORD = "dsid123"

Write-Host "Subindo rastreador $IdServidor"

& "$projectRoot\.venv\Scripts\python.exe" -c "
from src.clients.tracker_broker import executar_rastreador_broker
executar_rastreador_broker('$IdServidor')
"