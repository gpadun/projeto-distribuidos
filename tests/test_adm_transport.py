"""Tests for HTTP transport between ADM servers using mocked httpx."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.core.models import (
    IniciarEleicao,
    KeepAlive,
    NovoLider,
    RespostaEleicao,
    TipoServidor,
)
from src.core.serialization import to_message_dict
from src.infra.adm_transport import ADMHttpTransport, criar_adm_com_transporte_http
from src.servers.adm_server import ADMServer


def run(coro):
    return asyncio.run(coro)


ENDERECOS = {
    "adm-1": "http://127.0.0.1:8001",
    "adm-2": "http://127.0.0.1:8002",
    "adm-3": "http://127.0.0.1:8003",
}


def _configurar_mock_httpx():
    """Prepara mock do httpx.AsyncClient para testes async."""
    mock_client = AsyncMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    return mock_client, mock_context


def test_transport_monta_url_keepalive():
    transport = ADMHttpTransport(ENDERECOS)

    url = transport._url("adm-2", "/infra/keepalive")

    assert url == "http://127.0.0.1:8002/infra/keepalive"


def test_transport_envia_keepalive_com_url_e_json_corretos():
    transport = ADMHttpTransport(ENDERECOS)
    mensagem = KeepAlive(
        idServidor="adm-1",
        tipoServidor=TipoServidor.ADM,
        timestamp=1710000000,
    )
    mock_client, mock_context = _configurar_mock_httpx()

    with patch("src.infra.adm_transport.httpx.AsyncClient", return_value=mock_context):
        run(transport.enviar_keepalive("adm-2", mensagem))

    mock_client.post.assert_awaited_once_with(
        "http://127.0.0.1:8002/infra/keepalive",
        json=to_message_dict(mensagem),
    )


def test_transport_envia_iniciar_eleicao_no_path_correto():
    transport = ADMHttpTransport(ENDERECOS)
    mensagem = IniciarEleicao(
        idServidorOrigem="adm-1",
        idServidorDestino="adm-2",
        timestamp=1710000001,
    )
    mock_client, mock_context = _configurar_mock_httpx()

    with patch("src.infra.adm_transport.httpx.AsyncClient", return_value=mock_context):
        run(transport.enviar_eleicao("adm-2", mensagem))

    mock_client.post.assert_awaited_once_with(
        "http://127.0.0.1:8002/infra/eleicao/iniciar",
        json=to_message_dict(mensagem),
    )


def test_transport_envia_resposta_eleicao_no_path_correto():
    transport = ADMHttpTransport(ENDERECOS)
    mensagem = RespostaEleicao(
        idServidorOrigem="adm-2",
        idServidorDestino="adm-1",
        timestamp=1710000002,
    )
    mock_client, mock_context = _configurar_mock_httpx()

    with patch("src.infra.adm_transport.httpx.AsyncClient", return_value=mock_context):
        run(transport.enviar_eleicao("adm-1", mensagem))

    mock_client.post.assert_awaited_once_with(
        "http://127.0.0.1:8001/infra/eleicao/resposta",
        json=to_message_dict(mensagem),
    )


def test_transport_envia_novo_lider_no_path_correto():
    transport = ADMHttpTransport(ENDERECOS)
    mensagem = NovoLider(
        idServidor="adm-3",
        idLiderAnterior="adm-3",
        timestamp=1710000003,
    )
    mock_client, mock_context = _configurar_mock_httpx()

    with patch("src.infra.adm_transport.httpx.AsyncClient", return_value=mock_context):
        run(transport.enviar_eleicao("adm-1", mensagem))

    mock_client.post.assert_awaited_once_with(
        "http://127.0.0.1:8001/infra/eleicao/novo-lider",
        json=to_message_dict(mensagem),
    )


def test_criar_adm_com_transporte_http_executa_ciclo_keepalive():
    envios = []

    async def fake_keepalive(id_destino, mensagem):
        envios.append((id_destino, mensagem.tipoServidor, mensagem.idServidor))

    adm = ADMServer(
        id_servidor="adm-1",
        servidores_adm=["adm-1", "adm-2", "adm-3"],
        keepalive_sender=fake_keepalive,
    )

    run(adm.executar_ciclo_keepalive())

    assert sorted(dest for dest, _, _ in envios) == ["adm-2", "adm-3"]
    assert all(tipo == TipoServidor.ADM for _, tipo, _ in envios)
    assert all(origem == "adm-1" for _, _, origem in envios)


def test_criar_adm_com_transporte_http_configura_callbacks():
    adm = criar_adm_com_transporte_http(
        id_servidor="adm-1",
        enderecos_adm=ENDERECOS,
        servidores_adm=["adm-1", "adm-2", "adm-3"],
        eleicao_timeout=0.2,
    )

    assert adm.keepalive_sender is not None
    assert adm.election_sender is not None
    assert adm.on_lider_caiu is not None


class AsgiAdmPeerRouter:
    """Simula HTTP entre ADMs usando ASGITransport, sem rede real."""

    def __init__(self):
        self.adms: dict[str, ADMServer] = {}

    def registrar(self, id_adm: str, adm: ADMServer, app) -> None:
        self.adms[id_adm] = {"adm": adm, "app": app}

    async def enviar_keepalive(self, id_destino: str, mensagem: KeepAlive) -> None:
        app = self.adms[id_destino]["app"]
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/infra/keepalive",
                json=to_message_dict(mensagem),
            )
            assert response.status_code == 200

    async def enviar_eleicao(
        self,
        id_destino: str,
        mensagem: IniciarEleicao | RespostaEleicao | NovoLider,
    ) -> None:
        app = self.adms[id_destino]["app"]

        if isinstance(mensagem, IniciarEleicao):
            path = "/infra/eleicao/iniciar"
        elif isinstance(mensagem, RespostaEleicao):
            path = "/infra/eleicao/resposta"
        else:
            path = "/infra/eleicao/novo-lider"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(path, json=to_message_dict(mensagem))
            assert response.status_code == 200


def _criar_cluster_asgi(ids: list[str], router: AsgiAdmPeerRouter) -> dict[str, ADMServer]:
    adms = {}
    for id_adm in ids:
        adm = ADMServer(
            id_servidor=id_adm,
            servidores_adm=ids,
            keepalive_sender=router.enviar_keepalive,
            election_sender=router.enviar_eleicao,
            eleicao_timeout=0.2,
        )
        app = create_app(adm)
        router.registrar(id_adm, adm, app)
        adms[id_adm] = adm
    return adms


def test_transport_asgi_integra_keepalive_entre_dois_adms():
    router = AsgiAdmPeerRouter()
    adms = _criar_cluster_asgi(["adm-1", "adm-2"], router)

    run(adms["adm-1"].executar_ciclo_keepalive())

    assert "adm-1" in adms["adm-2"].servidores_adm_ativos


def test_transport_asgi_integra_eleicao_entre_tres_adms():
    router = AsgiAdmPeerRouter()
    adms = _criar_cluster_asgi(["adm-1", "adm-2", "adm-3"], router)

    for adm in adms.values():
        adm.servidores_adm_ativos.discard("adm-3")
        adm.lider_atual = "adm-3"
        adm.id_lider_anterior = "adm-3"

    router.adms.pop("adm-3", None)

    run(adms["adm-1"].iniciar_eleicao())

    assert adms["adm-1"].lider_atual == "adm-2"
    assert adms["adm-2"].lider_atual == "adm-2"