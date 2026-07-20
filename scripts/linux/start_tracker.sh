#!/usr/bin/env bash
# Equivalente Linux de scripts/start_tracker.ps1
# Uso: start_tracker.sh [id-servidor] [adm-url] [sup-url]
# Padrao: rastreador-1 (ADM lider detectado automaticamente; SUP derivado do id)
set -euo pipefail

ID_SERVIDOR="${1:-rastreador-1}"
ADM_URL_ARG="${2:-}"
SUP_URL_ARG="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
source "$SCRIPT_DIR/resolve_adm_lider.sh"

ADM_URL="$(resolve_adm_lider_url "$ADM_URL_ARG")"

if [ -z "$SUP_URL_ARG" ]; then
    case "$ID_SERVIDOR" in
        rastreador-1) SUP_URL_ARG="http://127.0.0.1:9101" ;;
        rastreador-2) SUP_URL_ARG="http://127.0.0.1:9102" ;;
        *) SUP_URL_ARG="" ;;
    esac
fi

export RABBITMQ_ENABLED=1
export RABBITMQ_HOST=127.0.0.1
export RABBITMQ_PORT=5672
export RABBITMQ_USER=dsid
export RABBITMQ_PASSWORD=dsid123
export ADM_URL
export ADM_URLS="http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003"
export SUP_URL="$SUP_URL_ARG"
export TRACKER_HEARTBEAT_INTERVAL=5

echo "Subindo rastreador $ID_SERVIDOR"
echo "ADM_URLS=$ADM_URLS SUP=$SUP_URL_ARG"

exec "$PROJECT_ROOT/.venv/bin/python" -c "
from src.clients.tracker_broker import executar_rastreador_broker
executar_rastreador_broker('$ID_SERVIDOR')
"
