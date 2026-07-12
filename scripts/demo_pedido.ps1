param(
    [string]$Url = "http://127.0.0.1:8003"
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

try {
    $response = Invoke-RestMethod -Uri "$Url/pedidos" -Method Post -Body $body -ContentType "application/json"
    Write-Host "SUCESSO"
    $response | ConvertTo-Json -Depth 5
}
catch {
    $status = $_.Exception.Response.StatusCode.value__
    Write-Host "FALHA - HTTP $status"

    $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
    $json = $reader.ReadToEnd() | ConvertFrom-Json
    $json | ConvertTo-Json -Depth 5
}