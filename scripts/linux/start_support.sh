#!/usr/bin/env bash
# Equivalente Linux de scripts/start_support.ps1
# Uso: start_support.sh [id-servidor] [id-rastreador] [porta]
# Padroes: sup-1 rastreador-1 9101
set -euo pipefail

ID_SERVIDOR="${1:-sup-1}"
ID_RASTREADOR="${2:-rastreador-1}"
PORT="${3:-9101}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

export SUP_ID="$ID_SERVIDOR"
export SUP_RASTREADOR="$ID_RASTREADOR"
export SUP_PORT="$PORT"
export SUP_HOST=127.0.0.1

echo "Subindo $SUP_ID para $ID_RASTREADOR em http://127.0.0.1:$PORT"

exec "$PROJECT_ROOT/.venv/bin/python" support_main.py
