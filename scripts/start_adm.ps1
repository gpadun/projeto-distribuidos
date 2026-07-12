param(
    [Parameter(Mandatory = $true)]
    [string]$AdmId,

    [Parameter(Mandatory = $true)]
    [int]$Port,

    [string]$Cluster = "adm-1,adm-2,adm-3"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$peers = switch ($AdmId) {
    "adm-1" { "adm-2:http://127.0.0.1:8002,adm-3:http://127.0.0.1:8003" }
    "adm-2" { "adm-1:http://127.0.0.1:8001,adm-3:http://127.0.0.1:8003" }
    "adm-3" { "adm-1:http://127.0.0.1:8001,adm-2:http://127.0.0.1:8002" }
    default { throw "ADM desconhecido: $AdmId" }
}

$env:ADM_ID = $AdmId
$env:ADM_PORT = "$Port"
$env:ADM_HOST = "127.0.0.1"
$env:ADM_CLUSTER = $Cluster
$env:ADM_PEERS = $peers
$env:ADM_HEARTBEAT_INTERVAL = "5"
$env:ADM_MONITOR_ENABLED = "1"
$env:ADM_HEARTBEAT_TIMEOUT = "10"

Write-Host "Subindo $AdmId em http://127.0.0.1:$Port"
Write-Host "Peers: $peers"

& "$projectRoot\.venv\Scripts\python.exe" main.py