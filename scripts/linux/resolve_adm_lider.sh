#!/usr/bin/env bash
# Descobre a URL do ADM lider atual.
# Uso: source resolve_adm_lider.sh; ADM_URL="$(resolve_adm_lider_url "$1")"

resolve_adm_lider_url() {
    local adm_url="${1:-}"
    if [ -n "$adm_url" ]; then
        printf '%s' "$adm_url"
        return 0
    fi

    local id url resp sou_lider lider_atual
    declare -A mapa=(
        [adm-1]="http://127.0.0.1:8001"
        [adm-2]="http://127.0.0.1:8002"
        [adm-3]="http://127.0.0.1:8003"
    )

    for id in adm-1 adm-2 adm-3; do
        url="${mapa[$id]}"
        resp="$(curl -s -m 2 "$url/infra/lider" || true)"
        [ -z "$resp" ] && continue

        sou_lider="$(printf '%s' "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('souLider', False))" 2>/dev/null || echo False)"
        if [ "$sou_lider" = "True" ]; then
            printf '%s' "$url"
            return 0
        fi

        lider_atual="$(printf '%s' "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('liderAtual',''))" 2>/dev/null || echo '')"
        if [ -n "$lider_atual" ] && [ -n "${mapa[$lider_atual]:-}" ]; then
            printf '%s' "${mapa[$lider_atual]}"
            return 0
        fi
    done

    echo "Nao foi possivel detectar o lider ADM; usando http://127.0.0.1:8003" >&2
    printf 'http://127.0.0.1:8003'
}
