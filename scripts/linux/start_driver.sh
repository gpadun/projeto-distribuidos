#!/usr/bin/env bash
# Equivalente Linux de scripts/start_driver.ps1
# Uso: start_driver.sh [id-entregador] [adm-url]
# Padrao: entregador-1 (ADM lider detectado automaticamente)
set -euo pipefail

ID_ENTREGADOR="${1:-entregador-1}"
ADM_URL_ARG="${2:-}"

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
export ADM_URLS="http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003"

echo "Entregador $ID_ENTREGADOR ouvindo PedidoDisponivel"
echo "ADM lider: $ADM_URL"

exec "$PROJECT_ROOT/.venv/bin/python" -m src.clients.mock_driver \
    --modo broker --id-entregador "$ID_ENTREGADOR" --adm-url "$ADM_URL"
