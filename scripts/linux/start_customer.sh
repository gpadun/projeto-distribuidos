#!/usr/bin/env bash
# Equivalente Linux de scripts/start_customer.ps1
# Uso: start_customer.sh [id-cliente] [acao] [id-pedido] [id-restaurante] [adm-url]
#   acao: criar | rastrear | demo (padrao) | confirmar
#   id-pedido: obrigatorio para "confirmar", opcional nos outros
#
# Exemplos:
#   start_customer.sh cliente-1 demo
#   start_customer.sh cliente-1 confirmar "UUID-DO-PEDIDO"
#   start_customer.sh cliente-2 demo
set -euo pipefail

ID_CLIENTE="${1:-cliente-1}"
ACAO="${2:-demo}"
ID_PEDIDO="${3:-}"
ID_RESTAURANTE="${4:-restaurante-1}"
ADM_URL_ARG="${5:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
source "$SCRIPT_DIR/resolve_adm_lider.sh"

ADM_URL="$(resolve_adm_lider_url "$ADM_URL_ARG")"

export RABBITMQ_ENABLED=1
export RABBITMQ_HOST=127.0.0.1
export RABBITMQ_PORT=5672
export RABBITMQ_USER=dsid
export RABBITMQ_PASSWORD=dsid123
export ADM_URL

echo "Cliente $ID_CLIENTE acao=$ACAO ADM=$ADM_URL"

ARGS=(-m src.clients.mock_customer --acao "$ACAO" --id-cliente "$ID_CLIENTE" --id-restaurante "$ID_RESTAURANTE" --adm-url "$ADM_URL")
if [ -n "$ID_PEDIDO" ]; then
    ARGS+=(--id-pedido "$ID_PEDIDO")
fi

exec "$PROJECT_ROOT/.venv/bin/python" "${ARGS[@]}"
