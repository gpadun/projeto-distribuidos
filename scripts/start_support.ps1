param(
    [string]$IdServidor = "sup-1",
    [string]$IdRastreador = "rastreador-1",
    [int]$Port = 9101
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$env:SUP_ID = $IdServidor
$env:SUP_RASTREADOR = $IdRastreador
$env:SUP_PORT = "$Port"
$env:SUP_HOST = "127.0.0.1"

Write-Host "Subindo $IdServidor para $IdRastreador em http://127.0.0.1:$Port"

& "$projectRoot\.venv\Scripts\python.exe" support_main.py