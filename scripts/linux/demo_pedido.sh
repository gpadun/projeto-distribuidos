#!/usr/bin/env bash
# Equivalente Linux de scripts/demo_pedido.ps1
# Uso: demo_pedido.sh [url] [tentativas]
# Padrao: http://127.0.0.1:8003, 3 tentativas
set -euo pipefail

URL="${1:-http://127.0.0.1:8003}"
TENTATIVAS="${2:-3}"

ID_PEDIDO="$(python3 -c 'import uuid; print(uuid.uuid4())')"
TS="$(date +%s)"
RESP_FILE="$(mktemp)"
trap 'rm -f "$RESP_FILE"' EXIT

echo "Tentando criar pedido em $URL"
echo "idPedido = $ID_PEDIDO"

for ((tentativa = 1; tentativa <= TENTATIVAS; tentativa++)); do
    http_code="$(curl -s -o "$RESP_FILE" -w '%{http_code}' -X POST "$URL/pedidos" \
        -H "Content-Type: application/json" \
        -d "{\"idPedido\":\"$ID_PEDIDO\",\"idCliente\":\"cliente-demo\",\"idRestaurante\":\"restaurante-1\",\"timestamp\":$TS}")"

    if [ "$http_code" = "200" ]; then
        echo "SUCESSO"
        python3 -m json.tool < "$RESP_FILE"
        exit 0
    fi

    echo "FALHA - HTTP $http_code (tentativa $tentativa/$TENTATIVAS)"
    python3 -m json.tool < "$RESP_FILE" 2>/dev/null || cat "$RESP_FILE"

    if [ "$tentativa" -lt "$TENTATIVAS" ] && { [ "$http_code" = "500" ] || [ "$http_code" = "503" ]; }; then
        echo "Aguardando 2s e tentando novamente com o mesmo idPedido..."
        sleep 2
        continue
    fi

    exit 1
done
