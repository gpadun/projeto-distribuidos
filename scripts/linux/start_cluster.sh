#!/usr/bin/env bash
# Equivalente Linux de scripts/start_cluster.ps1
# Tenta abrir 3 terminais novos (adm-1, adm-2, adm-3). Se nao encontrar um
# emulador de terminal conhecido, imprime os comandos para voce rodar
# manualmente em 3 abas/janelas.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CMD1="$SCRIPT_DIR/start_adm.sh adm-1 8001"
CMD2="$SCRIPT_DIR/start_adm.sh adm-2 8002"
CMD3="$SCRIPT_DIR/start_adm.sh adm-3 8003"

open_terminal() {
    local title="$1"
    local cmd="$2"

    if command -v gnome-terminal >/dev/null 2>&1; then
        gnome-terminal --title="$title" -- bash -c "$cmd; exec bash"
    elif command -v konsole >/dev/null 2>&1; then
        konsole -p tabtitle="$title" -e bash -c "$cmd; exec bash"
    elif command -v xfce4-terminal >/dev/null 2>&1; then
        xfce4-terminal --title="$title" -e "bash -c '$cmd; exec bash'"
    elif command -v xterm >/dev/null 2>&1; then
        xterm -T "$title" -e bash -c "$cmd; exec bash" &
    else
        return 1
    fi
}

if open_terminal "adm-1" "$CMD1" && open_terminal "adm-2" "$CMD2" && open_terminal "adm-3" "$CMD3"; then
    echo "Cluster ADM iniciado em 3 novos terminais:"
    echo "  adm-1 -> http://127.0.0.1:8001"
    echo "  adm-2 -> http://127.0.0.1:8002"
    echo "  adm-3 -> http://127.0.0.1:8003"
else
    echo "Nao foi possivel abrir terminais automaticamente" >&2
    echo "(nenhum de gnome-terminal/konsole/xfce4-terminal/xterm foi encontrado)." >&2
    echo "" >&2
    echo "Abra 3 terminais manualmente e rode um comando em cada um:" >&2
    echo "  $CMD1" >&2
    echo "  $CMD2" >&2
    echo "  $CMD3" >&2
    exit 1
fi

echo ""
echo "Aguarde 5-10 segundos para os heartbeats e depois rode:"
echo "  ./scripts/linux/demo_estado.sh"
