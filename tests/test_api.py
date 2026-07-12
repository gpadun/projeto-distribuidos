"""FastAPI endpoint tests."""

import asyncio

from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.servers.adm_server import ADMServer


def run(coro):
    return asyncio.run(coro)


def test_api_retorna_erro_limpo_para_pedido_inexistente():
    response = run(_post_aceitar_pedido_inexistente())

    assert response.status_code == 404
    assert response.json()["detail"] == "pedido nao encontrado"


async def _post_aceitar_pedido_inexistente():
    app = create_app(ADMServer("adm-1", ["rastreador-1"]))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(
            "/pedidos/aceitar",
            json={
                "idPedido": "00000000-0000-0000-0000-000000000001",
                "idEntregador": "entregador-1",
                "timestamp": 1,
            },
        )


def test_api_recebe_keepalive():
    adm = ADMServer("adm-2", servidores_adm=["adm-1", "adm-2"])
    app = create_app(adm)
    transport = ASGITransport(app=app)
    async def _post():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/infra/keepalive",
                json={
                    "idServidor": "adm-1",
                    "tipoServidor": "ADM",
                    "timestamp": 1,
                },
            )
    response = run(_post())
    assert response.status_code == 200
    assert "adm-1" in adm.servidores_adm_ativos


def test_api_recebe_iniciar_eleicao():
    adm = ADMServer("adm-2", servidores_adm=["adm-1", "adm-2"], eleicao_timeout=0.2)
    app = create_app(adm)
    transport = ASGITransport(app=app)

    async def _post():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/infra/eleicao/iniciar",
                json={"idServidorOrigem": "adm-1", "timestamp": 1},
            )

    response = run(_post())
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_api_recebe_resposta_eleicao():
    adm = ADMServer("adm-1", servidores_adm=["adm-1", "adm-2"])
    app = create_app(adm)
    transport = ASGITransport(app=app)

    async def _post():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/infra/eleicao/resposta",
                json={
                    "idServidorOrigem": "adm-2",
                    "idServidorDestino": "adm-1",
                    "timestamp": 1,
                },
            )

    response = run(_post())
    assert response.status_code == 200
    assert adm.recebeu_resposta_de_maior is True


def test_api_recebe_novo_lider():
    adm = ADMServer("adm-1", servidores_adm=["adm-1", "adm-2"])
    app = create_app(adm)
    transport = ASGITransport(app=app)

    async def _post():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/infra/eleicao/novo-lider",
                json={"idServidor": "adm-2", "timestamp": 1},
            )

    response = run(_post())
    assert response.status_code == 200
    assert adm.lider_atual == "adm-2"
    assert adm.aguardando_eleicao is False