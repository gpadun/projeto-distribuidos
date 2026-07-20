#!/usr/bin/env bash
# Equivalente Linux de scripts/start_restaurant.ps1
# Uso: start_restaurant.sh [id-restaurante] [adm-url] [--sem-preparo-auto]
# Padrao: restaurante-1 (ADM lider detectado automaticamente)
set -euo pipefail

ID_RESTAURANTE="${1:-restaurante-1}"
ADM_URL_ARG="${2:-}"
SEM_PREPARO_AUTO="${3:-}"

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

echo "Restaurante $ID_RESTAURANTE ouvindo PedidoDisponivel"
echo "ADM lider: $ADM_URL"

ARGS=(-m src.clients.mock_restaurant --id-restaurante "$ID_RESTAURANTE" --adm-url "$ADM_URL")
if [ "$SEM_PREPARO_AUTO" = "--sem-preparo-auto" ]; then
    ARGS+=(--sem-preparo-auto)
fi

exec "$PROJECT_ROOT/.venv/bin/python" "${ARGS[@]}"
