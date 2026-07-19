param(
    [int]$StartupTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logs = Join-Path $projectRoot "manual-test-logs"
$started = @()

New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Start-ProjectProcess {
    param(
        [string]$Name,
        [string]$Arguments,
        [hashtable]$EnvMap
    )

    $processInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $processInfo.FileName = $python
    $processInfo.Arguments = $Arguments
    $processInfo.WorkingDirectory = $projectRoot
    $processInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $processInfo.UseShellExecute = $true

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $processInfo
    $previousEnv = @{}
    try {
        foreach ($key in $EnvMap.Keys) {
            $previousEnv[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
            [Environment]::SetEnvironmentVariable($key, $EnvMap[$key], "Process")
        }
        [void]$process.Start()
    }
    finally {
        foreach ($key in $EnvMap.Keys) {
            [Environment]::SetEnvironmentVariable($key, $previousEnv[$key], "Process")
        }
    }

    $script:started += [pscustomobject]@{ Name = $Name; Process = $process }
    return $process
}

function Wait-Http {
    param(
        [string]$Url,
        [int]$Seconds = $StartupTimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 2
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "timeout esperando $Url"
}

function Wait-TrackerActive {
    param(
        [string]$AdmUrl,
        [string]$TrackerId,
        [int]$Seconds = $StartupTimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $estado = Invoke-RestMethod -Uri "$AdmUrl/estado" -Method Get -TimeoutSec 2
            if ($estado.rastreadoresAtivos -contains $TrackerId) {
                return $estado
            }
        }
        catch {
        }
        Start-Sleep -Milliseconds 500
    }
    throw "timeout esperando $TrackerId ficar ativo em $AdmUrl"
}

function Wait-Leader {
    param(
        [string]$AdmUrl,
        [string]$ExpectedLeader,
        [int]$Seconds = 30
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    $lastLeader = $null
    while ((Get-Date) -lt $deadline) {
        try {
            $lider = Invoke-RestMethod -Uri "$AdmUrl/infra/lider" -Method Get -TimeoutSec 2
            $lastLeader = $lider.liderAtual
            if ($lider.liderAtual -eq $ExpectedLeader -and $lider.souLider) {
                return $lider
            }
        }
        catch {
        }
        Start-Sleep -Milliseconds 500
    }
    throw "timeout esperando lider $ExpectedLeader em $AdmUrl (ultimo lider: $lastLeader)"
}

function Wait-OrderPrepared {
    param(
        [string]$AdmUrl,
        [string]$OrderId,
        [int]$Seconds = 20
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $estado = Invoke-RestMethod -Uri "$AdmUrl/estado" -Method Get -TimeoutSec 2
            $pedido = $estado.pedidosDetalhe.PSObject.Properties[$OrderId].Value
            if ($pedido -and $pedido.restaurantePreparou) {
                return $pedido
            }
        }
        catch {
        }
        Start-Sleep -Milliseconds 500
    }
    throw "timeout esperando restaurante preparar pedido $OrderId"
}

function Wait-OrderOnAdm {
    param(
        [string]$AdmUrl,
        [string]$OrderId,
        [int]$Seconds = 20
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $estado = Invoke-RestMethod -Uri "$AdmUrl/estado" -Method Get -TimeoutSec 2
            $pedido = $estado.pedidosDetalhe.PSObject.Properties[$OrderId].Value
            if ($pedido) {
                return $pedido
            }
        }
        catch {
        }
        Start-Sleep -Milliseconds 500
    }
    throw "timeout esperando pedido $OrderId em $AdmUrl"
}

function Stop-StartedProcesses {
    foreach ($item in $script:started) {
        try {
            if (-not $item.Process.HasExited) {
                Stop-Process -Id $item.Process.Id -Force
            }
        }
        catch {
        }
    }
}

try {
    Start-ProjectProcess "sup-1" "support_main.py" @{
        SUP_ID = "sup-1"
        SUP_RASTREADOR = "rastreador-1"
        SUP_PORT = "9101"
        SUP_HOST = "127.0.0.1"
    } | Out-Null
    Start-ProjectProcess "sup-2" "support_main.py" @{
        SUP_ID = "sup-2"
        SUP_RASTREADOR = "rastreador-2"
        SUP_PORT = "9102"
        SUP_HOST = "127.0.0.1"
    } | Out-Null
    Start-ProjectProcess "sup-3" "support_main.py" @{
        SUP_ID = "sup-3"
        SUP_RASTREADOR = "rastreador-3"
        SUP_PORT = "9103"
        SUP_HOST = "127.0.0.1"
    } | Out-Null

    Wait-Http "http://127.0.0.1:9101/estado" | Out-Null
    Wait-Http "http://127.0.0.1:9102/estado" | Out-Null
    Wait-Http "http://127.0.0.1:9103/estado" | Out-Null

    $admCommon = @{
        ADM_CLUSTER = "adm-1,adm-2,adm-3"
        ADM_TRACKERS = "rastreador-1,rastreador-2,rastreador-3"
        ADM_HEARTBEAT_INTERVAL = "2"
        ADM_MONITOR_ENABLED = "1"
        ADM_HEARTBEAT_TIMEOUT = "5"
        RABBITMQ_ENABLED = "1"
        RABBITMQ_HOST = "127.0.0.1"
        RABBITMQ_PORT = "5672"
        RABBITMQ_USER = "dsid"
        RABBITMQ_PASSWORD = "dsid123"
        SUP_URL_RASTREADOR_1 = "http://127.0.0.1:9101"
        SUP_URL_RASTREADOR_2 = "http://127.0.0.1:9102"
        ADM_SUPPORT_URLS = "rastreador-3:http://127.0.0.1:9103"
    }

    Start-ProjectProcess "adm-1" "main.py" ($admCommon + @{
        ADM_ID = "adm-1"
        ADM_PORT = "8001"
        ADM_HOST = "127.0.0.1"
        ADM_PEERS = "adm-2:http://127.0.0.1:8002,adm-3:http://127.0.0.1:8003"
    }) | Out-Null
    Start-ProjectProcess "adm-2" "main.py" ($admCommon + @{
        ADM_ID = "adm-2"
        ADM_PORT = "8002"
        ADM_HOST = "127.0.0.1"
        ADM_PEERS = "adm-1:http://127.0.0.1:8001,adm-3:http://127.0.0.1:8003"
    }) | Out-Null
    Start-ProjectProcess "adm-3" "main.py" ($admCommon + @{
        ADM_ID = "adm-3"
        ADM_PORT = "8003"
        ADM_HOST = "127.0.0.1"
        ADM_PEERS = "adm-1:http://127.0.0.1:8001,adm-2:http://127.0.0.1:8002"
    }) | Out-Null

    Wait-Http "http://127.0.0.1:8001/estado" | Out-Null
    Wait-Http "http://127.0.0.1:8002/estado" | Out-Null
    Wait-Http "http://127.0.0.1:8003/estado" | Out-Null
    Start-Sleep -Seconds 5

    Start-ProjectProcess "rastreador-3" "-c `"from src.clients.tracker_broker import executar_rastreador_broker; executar_rastreador_broker('rastreador-3')`"" @{
        RABBITMQ_ENABLED = "1"
        RABBITMQ_HOST = "127.0.0.1"
        RABBITMQ_PORT = "5672"
        RABBITMQ_USER = "dsid"
        RABBITMQ_PASSWORD = "dsid123"
        ADM_URL = "http://127.0.0.1:8003"
        ADM_URLS = "http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003"
        SUP_URL = "http://127.0.0.1:9103"
        TRACKER_HEARTBEAT_INTERVAL = "2"
    } | Out-Null
    $estadoComR3 = Wait-TrackerActive "http://127.0.0.1:8003" "rastreador-3"

    Start-ProjectProcess "restaurante-1" "-m src.clients.mock_restaurant --id-restaurante restaurante-1 --adm-url http://127.0.0.1:8003" @{
        RABBITMQ_ENABLED = "1"
        RABBITMQ_HOST = "127.0.0.1"
        RABBITMQ_PORT = "5672"
        RABBITMQ_USER = "dsid"
        RABBITMQ_PASSWORD = "dsid123"
        ADM_URL = "http://127.0.0.1:8003"
    } | Out-Null
    Start-Sleep -Seconds 3

    $liderAntes = Invoke-RestMethod -Uri "http://127.0.0.1:8003/infra/lider" -Method Get
    $idPedido = [guid]::NewGuid().ToString()
    $timestamp = [int][double]::Parse((Get-Date -UFormat %s))
    $criarPedidoBody = @{
        idPedido = $idPedido
        idCliente = "cliente-manual"
        idRestaurante = "restaurante-1"
        timestamp = $timestamp
    } | ConvertTo-Json

    $pedido = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8003/pedidos" `
        -Method Post `
        -Body $criarPedidoBody `
        -ContentType "application/json"

    Wait-OrderOnAdm "http://127.0.0.1:8001" $idPedido | Out-Null
    Wait-OrderOnAdm "http://127.0.0.1:8002" $idPedido | Out-Null
    $pedidoAposRestaurante = Wait-OrderPrepared "http://127.0.0.1:8003" $idPedido
    Wait-OrderPrepared "http://127.0.0.1:8001" $idPedido | Out-Null
    Wait-OrderPrepared "http://127.0.0.1:8002" $idPedido | Out-Null
    $adm3 = ($started | Where-Object Name -eq "adm-3").Process
    Stop-Process -Id $adm3.Id -Force

    $liderDepois = Wait-Leader "http://127.0.0.1:8002" "adm-2"
    Wait-OrderOnAdm "http://127.0.0.1:8002" $idPedido | Out-Null
    $confirmarBody = @{
        idPedido = $idPedido
        idCliente = "cliente-manual"
        timestamp = [int][double]::Parse((Get-Date -UFormat %s))
    } | ConvertTo-Json
    $confirmado = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8002/pedidos/confirmar" `
        -Method Post `
        -Body $confirmarBody `
        -ContentType "application/json"

    [pscustomobject]@{
        liderAntes = $liderAntes.liderAtual
        pedidoCriadoNoLider = $pedido.idPedido
        restaurantePreparou = $pedidoAposRestaurante.restaurantePreparou
        rastreadorDinamicoAtivo = "rastreador-3"
        rastreadoresAtivosAntesDaFalha = $estadoComR3.rastreadoresAtivos
        liderDepoisDaFalhaAdm3 = $liderDepois.liderAtual
        pedidoConfirmadoNoNovoLider = $confirmado.idPedido
        statusConfirmacao = $confirmado.status
        logs = $logs
    } | ConvertTo-Json -Depth 5
}
finally {
    Stop-StartedProcesses
}
