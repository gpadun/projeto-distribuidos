function Resolve-AdmLiderUrl {
    param(
        [string]$AdmUrl = ""
    )

    if ($AdmUrl -and $AdmUrl.Trim()) {
        return $AdmUrl.Trim()
    }

    $mapa = @{
        "adm-1" = "http://127.0.0.1:8001"
        "adm-2" = "http://127.0.0.1:8002"
        "adm-3" = "http://127.0.0.1:8003"
    }

    foreach ($url in $mapa.Values) {
        try {
            $lider = Invoke-RestMethod -Uri "$url/infra/lider" -Method Get -TimeoutSec 2
            if ($lider.souLider) {
                return $url
            }
            if ($lider.liderAtual -and $mapa.ContainsKey($lider.liderAtual)) {
                return $mapa[$lider.liderAtual]
            }
        }
        catch {
            continue
        }
    }

    Write-Warning "Nao foi possivel detectar o lider ADM; usando http://127.0.0.1:8003"
    return "http://127.0.0.1:8003"
}
