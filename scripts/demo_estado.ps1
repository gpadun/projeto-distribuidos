$adms = @(
    @{ id = "adm-1"; url = "http://127.0.0.1:8001" },
    @{ id = "adm-2"; url = "http://127.0.0.1:8002" },
    @{ id = "adm-3"; url = "http://127.0.0.1:8003" }
)

foreach ($adm in $adms) {
    Write-Host ""
    Write-Host "===== $($adm.id) ====="
    try {
        $lider = Invoke-RestMethod -Uri "$($adm.url)/infra/lider" -Method Get
        $estado = Invoke-RestMethod -Uri "$($adm.url)/estado" -Method Get

        Write-Host "souLider       : $($lider.souLider)"
        Write-Host "liderAtual     : $($lider.liderAtual)"
        Write-Host "admsAtivos     : $($estado.admsAtivos -join ', ')"
        Write-Host "rastreadoresAtivos: $($estado.rastreadoresAtivos -join ', ')"
        if (-not $estado.rastreadoresAtivos) {
            Write-Host "  (vazio e normal antes de subir os rastreadores)"
        }
        Write-Host "rastreadoresExpirados: $($estado.rastreadoresComHeartbeatExpirado -join ', ')"
        Write-Host "aguardandoEleicao : $($estado.aguardandoEleicao)"
        Write-Host "idLiderAnterior   : $($estado.idLiderAnterior)"
        Write-Host "roteamento        : $($estado.roteamento | ConvertTo-Json -Compress)"
    }
    catch {
        Write-Host "OFFLINE ou erro: $($_.Exception.Message)"
    }
}