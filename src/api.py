"""FastAPI entrypoint for synchronous command messages."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from src.broker.factory import criar_publisher, fechar_publisher
from src.broker.publisher import Publisher
from src.core.models import (
    AceitarPedido,
    ConfirmarEntrega,
    CriarPedido,
    IniciarEleicao,
    KeepAlive,
    NovoLider,
    RespostaEleicao,
)
from src.infra.adm_transport import criar_adm_com_transporte_http
from src.servers.adm_server import ADMServer, NaoELiderError


def parse_adm_peers(raw: str) -> dict[str, str]:
    enderecos = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        id_adm, url = item.split(":", 1)
        enderecos[id_adm.strip()] = url.strip()
    return enderecos


def _carregar_support_urls() -> dict[str, str]:
    mapping = {
        "rastreador-1": os.getenv("SUP_URL_RASTREADOR_1", ""),
        "rastreador-2": os.getenv("SUP_URL_RASTREADOR_2", ""),
    }
    return {k: v for k, v in mapping.items() if v}


def _criar_adm_padrao(publisher: Publisher | None) -> ADMServer:
    """Build the default ADM instance for this process."""
    id_servidor = os.getenv("ADM_ID", "adm-1")
    servidores_adm = [
        servidor.strip()
        for servidor in os.getenv("ADM_CLUSTER", "adm-1,adm-2,adm-3").split(",")
        if servidor.strip()
    ]
    servidores_rastreadores = ["rastreador-1", "rastreador-2"]
    peers_raw = os.getenv("ADM_PEERS", "")
    enderecos = parse_adm_peers(peers_raw) if peers_raw else {}
    support_urls = _carregar_support_urls()
    heartbeat_timeout = float(os.getenv("ADM_HEARTBEAT_TIMEOUT", "10"))

    if enderecos:
        return criar_adm_com_transporte_http(
            id_servidor=id_servidor,
            enderecos_adm=enderecos,
            servidores_adm=servidores_adm,
            servidores_rastreadores=servidores_rastreadores,
            publisher=publisher,
            support_urls=support_urls,
            heartbeat_timeout=heartbeat_timeout,
        )

    return ADMServer(
        id_servidor=id_servidor,
        servidores_adm=servidores_adm,
        servidores_rastreadores=servidores_rastreadores,
        publisher=publisher,
        support_urls=support_urls,
        heartbeat_timeout=heartbeat_timeout,
    )


def _exception_detail(exc: Exception) -> str:
    """Return a clean API error message without KeyError's extra quotes."""
    return str(exc.args[0]) if exc.args else str(exc)


def _http_exception_nao_lider(exc: NaoELiderError) -> HTTPException:
    """Tell the client which ADM is the leader so it can resend the request."""
    return HTTPException(
        status_code=409,
        detail={
            "mensagem": "este servidor ADM nao e o lider; reenvie o comando ao lider atual",
            "idServidor": exc.id_servidor,
            "liderAtual": exc.lider_atual,
        },
    )


def create_app(adm_server: ADMServer | None = None) -> FastAPI:
    """Create an API app backed by one ADMServer instance."""
    app_publisher = None

    if adm_server is None:
        app_publisher = criar_publisher()
        adm = _criar_adm_padrao(app_publisher)
    else:
        adm = adm_server

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async def loop_monitoramento():
            intervalo = float(os.getenv("ADM_HEARTBEAT_INTERVAL", "5"))
            while True:
                await adm.executar_ciclo_monitoramento()
                await asyncio.sleep(intervalo)

        task = asyncio.create_task(loop_monitoramento())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            fechar_publisher(app_publisher)

    monitor_enabled = os.getenv("ADM_MONITOR_ENABLED", "1") == "1"
    use_lifespan = monitor_enabled and adm_server is None

    if use_lifespan:
        app = FastAPI(title="Sistema Distribuido de Rastreamento", lifespan=lifespan)
    else:
        app = FastAPI(title="Sistema Distribuido de Rastreamento")

    @app.post("/pedidos")
    async def criar_pedido(requisicao: CriarPedido):
        try:
            return await adm.criar_pedido(requisicao)
        except NaoELiderError as exc:
            raise _http_exception_nao_lider(exc) from exc

    @app.post("/pedidos/aceitar")
    async def aceitar_pedido(requisicao: AceitarPedido):
        try:
            return await adm.aceitar_pedido(requisicao)
        except NaoELiderError as exc:
            raise _http_exception_nao_lider(exc) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=_exception_detail(exc)) from exc

    @app.post("/pedidos/confirmar")
    async def confirmar_entrega(requisicao: ConfirmarEntrega):
        try:
            return await adm.confirmar_entrega(requisicao)
        except NaoELiderError as exc:
            raise _http_exception_nao_lider(exc) from exc
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

    @app.post("/infra/eleicao/iniciar")
    async def receber_iniciar_eleicao(mensagem: IniciarEleicao):
        await adm.processar_iniciar_eleicao(mensagem)
        return {"ok": True}

    @app.post("/infra/eleicao/resposta")
    async def receber_resposta_eleicao(mensagem: RespostaEleicao):
        await adm.processar_resposta_eleicao(mensagem)
        return {"ok": True}

    @app.post("/infra/eleicao/novo-lider")
    async def receber_novo_lider(mensagem: NovoLider):
        await adm.processar_novo_lider(mensagem)
        return {"ok": True}

    @app.get("/infra/lider")
    async def consultar_lider():
        return {
            "idServidor": adm.id_servidor,
            "liderAtual": adm.lider_atual,
            "souLider": adm.sou_lider(),
        }

    @app.get("/estado")
    async def estado():
        return {
            "idServidor": adm.id_servidor,
            "liderAtual": adm.lider_atual,
            "souLider": adm.sou_lider(),
            "pedidos": list(adm.pedidos.keys()),
            "roteamento": {str(k): v for k, v in adm.mapa_pedido_servidor.items()},
            "rastreadoresAtivos": sorted(adm.servidores_rastreadores_ativos),
            "rastreadoresComHeartbeatExpirado": adm.servidores_com_heartbeat_expirado(),
            "admsAtivos": sorted(adm.servidores_adm_ativos),
            "admsComHeartbeatExpirado": adm.adms_com_heartbeat_expirado(),
            "liderDisponivel": adm.lider_disponivel,
            "aguardandoEleicao": adm.aguardando_eleicao,
            "idLiderAnterior": adm.id_lider_anterior,
            "rabbitmqHabilitado": app_publisher is not None,
        }

    return app


app = create_app()