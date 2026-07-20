#!/usr/bin/env bash
# Equivalente Linux de scripts/start_adm.ps1
# Uso: start_adm.sh <adm-id> <port>
set -euo pipefail

ADM_ID="${1:?uso: start_adm.sh <adm-id> <port>}"
PORT="${2:?uso: start_adm.sh <adm-id> <port>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

case "$ADM_ID" in
    adm-1) PEERS="adm-2:http://127.0.0.1:8002,adm-3:http://127.0.0.1:8003" ;;
    adm-2) PEERS="adm-1:http://127.0.0.1:8001,adm-3:http://127.0.0.1:8003" ;;
    adm-3) PEERS="adm-1:http://127.0.0.1:8001,adm-2:http://127.0.0.1:8002" ;;
    *)
        echo "ADM desconhecido: $ADM_ID" >&2
        exit 1
        ;;
esac

export ADM_ID
export ADM_PORT="$PORT"
export ADM_HOST=127.0.0.1
export ADM_CLUSTER="adm-1,adm-2,adm-3"
export ADM_PEERS="$PEERS"
export ADM_HEARTBEAT_INTERVAL=5
export ADM_MONITOR_ENABLED=1
export ADM_HEARTBEAT_TIMEOUT=10
export RABBITMQ_ENABLED=1
export RABBITMQ_HOST=127.0.0.1
export RABBITMQ_PORT=5672
export RABBITMQ_USER=dsid
export RABBITMQ_PASSWORD=dsid123
export SUP_URL_RASTREADOR_1=http://127.0.0.1:9101
export SUP_URL_RASTREADOR_2=http://127.0.0.1:9102

echo "Subindo $ADM_ID em http://127.0.0.1:$PORT"
echo "Peers: $PEERS"

exec "$PROJECT_ROOT/.venv/bin/python" main.py
