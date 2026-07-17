param(
    [string]$AdmUrl = "http://127.0.0.1:8003"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "===== Estado ADM lider ($AdmUrl) ====="
try {
    $estado = Invoke-RestMethod -Uri "$AdmUrl/estado" -Method Get
    Write-Host "idServidor                      : $($estado.idServidor)"
    Write-Host "souLider                        : $($estado.souLider)"
    Write-Host "liderAtual                      : $($estado.liderAtual)"
    Write-Host "rastreadoresAtivos              : $($estado.rastreadoresAtivos -join ', ')"
    Write-Host "rastreadoresComHeartbeatExpirado: $($estado.rastreadoresComHeartbeatExpirado -join ', ')"
    if (-not $estado.rastreadoresAtivos) {
        Write-Host "(normal antes de subir os rastreadores)"
    }
    if ($estado.rastreadoresComHeartbeatExpirado) {
        Write-Host "(expirado = sem keepalive recente; suba os rastreadores ou aguarde failover)"
    }
    Write-Host "roteamento                      : $($estado.roteamento | ConvertTo-Json -Compress)"
}
catch {
    Write-Host "Erro ao consultar ADM: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "===== SUPs ====="
foreach ($sup in @("http://127.0.0.1:9101", "http://127.0.0.1:9102")) {
    Write-Host ""
    Write-Host "--- $sup ---"
    try {
        $estadoSup = Invoke-RestMethod -Uri "$sup/estado" -Method Get
        Write-Host "idServidor            : $($estadoSup.idServidor)"
        Write-Host "idRastreadorAssociado : $($estadoSup.idRastreadorAssociado)"
        Write-Host "pedidosNoBackup       : $($estadoSup.pedidosNoBackup)"
        Write-Host "ultimoSync            : $($estadoSup.ultimoSync)"
    }
    catch {
        Write-Host "OFFLINE ou erro: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "Dica: mate o rastreador que aparece no log do entregador (rastreador=...)."
Write-Host "Aguarde ~15s (timeout 10s + intervalo monitor 5s) e rode este script de novo."
