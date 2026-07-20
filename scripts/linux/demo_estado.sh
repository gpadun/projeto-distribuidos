#!/usr/bin/env bash
# Equivalente Linux de scripts/demo_estado.ps1
set -euo pipefail

for port in 8001 8002 8003; do
    echo ""
    echo "===== adm (porta $port) ====="
    lider="$(curl -s -m 3 "http://127.0.0.1:$port/infra/lider" || true)"
    if [ -z "$lider" ]; then
        echo "OFFLINE ou erro"
        continue
    fi
    echo "$lider" | python3 -m json.tool
    curl -s -m 3 "http://127.0.0.1:$port/estado" | python3 -m json.tool
done
