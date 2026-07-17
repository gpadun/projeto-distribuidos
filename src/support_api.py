"""HTTP API for a Support server (SUP) backup process."""

from fastapi import FastAPI

from src.servers.support_server import SupportServer


def create_support_app(
    id_servidor: str,
    id_rastreador: str,
) -> FastAPI:
    sup = SupportServer(id_servidor, id_rastreador)
    app = FastAPI(title=f"SUP {id_servidor}")

    @app.post("/sync")
    async def sincronizar(rastreios: dict):
        await sup.sincronizar_rastreios(rastreios)
        return {"ok": True, "pedidos": len(rastreios)}
    
    @app.get("/backup")
    async def backup():
        return await sup.enviar_lista_backup()
    
    @app.get("/estado")
    async def estado():
        return {
            "idServidor": sup.id_servidor,
            "idRastreadorAssociado": sup.id_servidor_rastreador_associado,
            "pedidosNoBackup": len(sup.rastreios),
            "ultimoSync": sup.ultimo_sync,
        }
    
    return app