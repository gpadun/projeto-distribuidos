$adms = @(
    @{ id = "adm-1"; url = "http://127.0.0.1:8001" },
    @{ id = "adm-2"; url = "http://127.0.0.1:8002" },
    @{ id = "adm-3"; url = "http://127.0.0.1:8003" }
)

foreach ($adm in $adms) {
    Write-Host ""
    Write-Host "===== $($adm.id) ====="
    try {
        $estado = Invoke-RestMethod -Uri "$($adm.url)/estado" -Method Get -TimeoutSec 3
        Write-Host "liderAtual     : $($estado.liderAtual)"
        Write-Host "souLider       : $($estado.souLider)"
        Write-Host "roteamento     : $($estado.roteamento | ConvertTo-Json -Compress)"
        Write-Host "pedidos        : $($estado.pedidos.Count)"
    }
    catch {
        Write-Host "OFFLINE ou erro: $($_.Exception.Message)"
    }
}
