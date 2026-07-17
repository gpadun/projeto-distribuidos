"""HTTP API for a Support server (SUP) backup process."""

from fastapi import FastAPI

from src.presentation_log import log_apresentacao
from src.servers.support_server import SupportServer


def create_support_app(
    id_servidor: str,
    id_rastreador: str,
) -> FastAPI:
    sup = SupportServer(id_servidor, id_rastreador)
    pedidos_sync_logados: set[str] = set()
    app = FastAPI(title=f"SUP {id_servidor}")

    @app.post("/sync")
    async def sincronizar(rastreios: dict):
        novos = set(rastreios.keys()) - pedidos_sync_logados
        await sup.sincronizar_rastreios(rastreios)
        if novos:
            pedidos_sync_logados.update(novos)
            log_apresentacao(
                f"sup {id_servidor}",
                f"sync recebido de {id_rastreador}: pedido(s) {', '.join(sorted(novos))}",
            )
        return {"ok": True, "pedidos": len(rastreios)}
    
    @app.get("/backup")
    async def backup():
        dados = await sup.enviar_lista_backup()
        log_apresentacao(
            f"sup {id_servidor}",
            f"backup enviado ao ADM: {len(dados)} pedido(s) de {id_rastreador}",
        )
        return dados
    
    @app.get("/estado")
    async def estado():
        return {
            "idServidor": sup.id_servidor,
            "idRastreadorAssociado": sup.id_servidor_rastreador_associado,
            "pedidosNoBackup": len(sup.rastreios),
            "ultimoSync": sup.ultimo_sync,
        }
    
    return app