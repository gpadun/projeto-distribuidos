"""FastAPI entrypoint for synchronous command messages."""

from fastapi import FastAPI, HTTPException

from src.core.models import AceitarPedido, ConfirmarEntrega, CriarPedido, KeepAlive
from src.servers.adm_server import ADMServer


def _exception_detail(exc: Exception) -> str:
    """Return a clean API error message without KeyError's extra quotes."""
    return str(exc.args[0]) if exc.args else str(exc)


def create_app(adm_server: ADMServer | None = None) -> FastAPI:
    """Create an API app backed by one ADMServer instance."""
    adm = adm_server or ADMServer(
        id_servidor="adm-1",
        servidores_rastreadores=["rastreador-1", "rastreador-2"],
        servidores_adm=["adm-1", "adm-2"],
    )
    app = FastAPI(title="Sistema Distribuido de Rastreamento")

    @app.post("/pedidos")
    async def criar_pedido(requisicao: CriarPedido):
        return await adm.criar_pedido(requisicao)

    @app.post("/pedidos/aceitar")
    async def aceitar_pedido(requisicao: AceitarPedido):
        try:
            return await adm.aceitar_pedido(requisicao)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=_exception_detail(exc)) from exc

    @app.post("/pedidos/confirmar")
    async def confirmar_entrega(requisicao: ConfirmarEntrega):
        try:
            return await adm.confirmar_entrega(requisicao)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=_exception_detail(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=_exception_detail(exc)) from exc

    @app.post("/infra/keepalive")
    async def keepalive(mensagem: KeepAlive):
        await adm.processar_keepalive(mensagem)
        return {"ok": True}

    @app.post("/infra/eleicao")
    async def eleicao():
        lider = await adm.iniciar_eleicao()
        return {"lider": lider}

    @app.get("/estado")
    async def estado():
        return {
            "liderAtual": adm.lider_atual,
            "pedidos": list(adm.pedidos.keys()),
            "roteamento": {str(k): v for k, v in adm.mapa_pedido_servidor.items()},
            "rastreadoresAtivos": sorted(adm.servidores_rastreadores_ativos),
            "admsAtivos": sorted(adm.servidores_adm_ativos),
            "admsComHeartbeatExpirado": adm.adms_com_heartbeat_expirado(),
        }

    return app


app = create_app()
