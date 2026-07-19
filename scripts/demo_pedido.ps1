param(
    [string]$Url = "http://127.0.0.1:8003",
    [int]$Tentativas = 3
)

$idPedido = [guid]::NewGuid().ToString()

$body = @{
    idPedido = $idPedido
    idCliente = "cliente-demo"
    idRestaurante = "restaurante-1"
    timestamp = [int][double]::Parse((Get-Date -UFormat %s))
} | ConvertTo-Json

Write-Host "Tentando criar pedido em $Url"
Write-Host "idPedido = $idPedido"

for ($tentativa = 1; $tentativa -le $Tentativas; $tentativa++) {
    try {
        $response = Invoke-RestMethod -Uri "$Url/pedidos" -Method Post -Body $body -ContentType "application/json"
        Write-Host "SUCESSO"
        $response | ConvertTo-Json -Depth 5
        exit 0
    }
    catch {
        $status = $_.Exception.Response.StatusCode.value__
        Write-Host "FALHA - HTTP $status (tentativa $tentativa/$Tentativas)"

        $corpo = ""
        if ($_.Exception.Response -ne $null) {
            $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
            $corpo = $reader.ReadToEnd()
        }
        if ($corpo) {
            try {
                $corpo | ConvertFrom-Json | ConvertTo-Json -Depth 5
            }
            catch {
                Write-Host $corpo
            }
        }

        if ($tentativa -lt $Tentativas -and ($status -eq 500 -or $status -eq 503)) {
            Write-Host "Aguardando 2s e tentando novamente com o mesmo idPedido..."
            Start-Sleep -Seconds 2
            continue
        }

        exit 1
    }
}
