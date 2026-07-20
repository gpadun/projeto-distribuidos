#!/usr/bin/env bash
# Equivalente Linux de scripts/demo_falha_rastreador.ps1
# Uso: demo_falha_rastreador.sh [adm-url]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/resolve_adm_lider.sh"

ADM_URL="$(resolve_adm_lider_url "${1:-}")"

echo ""
echo "===== Estado ADM lider ($ADM_URL) ====="
estado="$(curl -s -m 3 "$ADM_URL/estado" || true)"
if [ -z "$estado" ]; then
    echo "Erro ao consultar ADM"
else
    echo "$estado" | python3 -m json.tool
fi

echo ""
echo "===== SUPs ====="
for sup in "http://127.0.0.1:9101" "http://127.0.0.1:9102"; do
    echo ""
    echo "--- $sup ---"
    resp="$(curl -s -m 3 "$sup/estado" || true)"
    if [ -z "$resp" ]; then
        echo "OFFLINE ou erro"
    else
        echo "$resp" | python3 -m json.tool
    fi
done

echo ""
echo "Dica: mate o rastreador que aparece no log do entregador (rastreador=...)."
echo "Aguarde ~15s (timeout 10s + intervalo monitor 5s) e rode este script de novo."
