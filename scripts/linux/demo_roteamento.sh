#!/usr/bin/env bash
# Equivalente Linux de scripts/demo_roteamento.ps1
set -euo pipefail

for port in 8001 8002 8003; do
    echo ""
    echo "===== adm (porta $port) ====="
    estado="$(curl -s -m 3 "http://127.0.0.1:$port/estado" || true)"
    if [ -z "$estado" ]; then
        echo "OFFLINE ou erro"
        continue
    fi
    echo "$estado" | python3 -m json.tool
done
