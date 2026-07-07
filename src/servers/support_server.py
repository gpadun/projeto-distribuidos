"""Support server (SUP) that keeps a secondary copy of tracker state."""

from copy import deepcopy
from time import time
from typing import Any


class SupportServer:
    """Keeps backup tracking data for one associated TrackerServer."""

    def __init__(self, id_servidor: str, id_servidor_rastreador_associado: str):
        self.id_servidor = id_servidor
        self.id_servidor_rastreador_associado = id_servidor_rastreador_associado
        self.rastreios: dict[str, dict[str, Any]] = {}
        self.ultimo_sync: float | None = None

    async def sincronizar_rastreios(self, rastreios: dict) -> None:
        """Replace the local backup with the newest tracker snapshot."""
        self.rastreios = deepcopy(rastreios)
        self.ultimo_sync = time()

    async def enviar_lista_backup(self) -> dict:
        """Return the latest tracking backup known by this support server."""
        return deepcopy(self.rastreios)
