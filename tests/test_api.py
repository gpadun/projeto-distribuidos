"""FastAPI endpoint tests."""

import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.servers.adm_server import ADMServer


def run(coro):
    return asyncio.run(coro)


def test_api_retorna_erro_limpo_para_pedido_inexistente():
    adm = ADMServer("adm-1", ["rastreador-1"])
    adm.lider_atual = "adm-1"
    response = run(_post_aceitar_pedido_inexistente(adm))

    assert response.status_code == 404
    assert response.json()["detail"] == "pedido nao encontrado"


def test_api_retorna_erro_limpo_quando_nao_ha_rastreador_ativo():
    adm = ADMServer("adm-1", ["rastreador-1"], servidores_adm=["adm-1"])
    adm.lider_atual = "adm-1"
    response = run(_post_aceitar_sem_rastreador_ativo(adm))

    assert response.status_code == 503
    assert response.json()["detail"] == "nenhum servidor rastreador ativo"


async def _post_aceitar_pedido_inexistente(adm: ADMServer):
    app = create_app(adm)
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


async def _post_aceitar_sem_rastreador_ativo(adm: ADMServer):
    app = create_app(adm)
    transport = ASGITransport(app=app)
    id_pedido = "00000000-0000-0000-0000-000000000002"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/pedidos",
            json={
                "idPedido": id_pedido,
                "idCliente": "cliente-1",
                "idRestaurante": "restaurante-1",
                "timestamp": 1,
            },
        )
        return await client.post(
            "/pedidos/aceitar",
            json={
                "idPedido": id_pedido,
                "idEntregador": "entregador-1",
                "timestamp": 2,
            },
        )


def test_api_rejeita_criar_pedido_quando_nao_e_lider():
    adm = ADMServer("adm-1", servidores_adm=["adm-1", "adm-2", "adm-3"])
    adm.lider_atual = "adm-3"
    app = create_app(adm)
    transport = ASGITransport(app=app)

    async def _post():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/pedidos",
                json={
                    "idPedido": str(uuid4()),
                    "idCliente": "cliente-1",
                    "idRestaurante": "restaurante-1",
                    "timestamp": 1,
                },
            )

    response = run(_post())

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "mensagem": "este servidor ADM nao e o lider; reenvie o comando ao lider atual",
        "idServidor": "adm-1",
        "liderAtual": "adm-3",
    }
    assert len(adm.pedidos) == 0


def test_api_lider_pode_criar_pedido():
    adm = ADMServer("adm-3", servidores_adm=["adm-1", "adm-2", "adm-3"])
    adm.lider_atual = "adm-3"
    app = create_app(adm)
    transport = ASGITransport(app=app)
    id_pedido = str(uuid4())

    async def _post():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/pedidos",
                json={
                    "idPedido": id_pedido,
                    "idCliente": "cliente-1",
                    "idRestaurante": "restaurante-1",
                    "timestamp": 1,
                },
            )

    response = run(_post())

    assert response.status_code == 200
    assert response.json()["idPedido"] == id_pedido


def test_api_rejeita_aceitar_pedido_quando_nao_e_lider():
    adm = ADMServer("adm-2", servidores_adm=["adm-1", "adm-2", "adm-3"])
    adm.lider_atual = "adm-3"
    app = create_app(adm)
    transport = ASGITransport(app=app)

    async def _post():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/pedidos/aceitar",
                json={
                    "idPedido": "00000000-0000-0000-0000-000000000001",
                    "idEntregador": "entregador-1",
                    "timestamp": 1,
                },
            )

    response = run(_post())

    assert response.status_code == 409
    assert response.json()["detail"]["liderAtual"] == "adm-3"
    assert response.json()["detail"]["idServidor"] == "adm-2"


def test_api_consultar_lider():
    adm = ADMServer("adm-2", servidores_adm=["adm-1", "adm-2", "adm-3"])
    adm.lider_atual = "adm-3"
    app = create_app(adm)
    transport = ASGITransport(app=app)

    async def _get():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/infra/lider")

    response = run(_get())

    assert response.status_code == 200
    assert response.json() == {
        "idServidor": "adm-2",
        "liderAtual": "adm-3",
        "souLider": False,
    }


def test_demo_page_disponivel():
    adm = ADMServer("adm-1", servidores_adm=["adm-1"])
    app = create_app(adm)
    transport = ASGITransport(app=app)

    async def _get():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/demo")

    response = run(_get())

    assert response.status_code == 200
    assert "Painel DSID" in response.text
    assert "demo/cluster" in response.text
    assert "Preparar restaurante" in response.text
    assert "Fluxo Distribuido" in response.text
    assert "Etapas do Pedido" in response.text
    assert "route-percent" in response.text
    assert "GPS aguardando" in response.text
    assert "Demo rápida" in response.text


def test_demo_cluster_retorna_estado_local():
    adm = ADMServer("adm-1", servidores_adm=["adm-1", "adm-2"])
    adm.lider_atual = "adm-1"
    app = create_app(adm)
    transport = ASGITransport(app=app)

    async def _get():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/demo/cluster")

    response = run(_get())

    assert response.status_code == 200
    body = response.json()
    assert body["idServidor"] == "adm-1"
    assert body["liderAtual"] == "adm-1"
    assert body["estados"][0]["idServidor"] == "adm-1"
    assert body["estados"][0]["online"] is True
    assert body["estados"][1] == {"idServidor": "adm-2", "online": False}


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


def test_api_preparar_pedido():
    adm = ADMServer("adm-1", servidores_adm=["adm-1"])
    adm.lider_atual = "adm-1"
    app = create_app(adm)
    transport = ASGITransport(app=app)
    id_pedido = str(uuid4())

    async def _post():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/pedidos",
                json={
                    "idPedido": id_pedido,
                    "idCliente": "cliente-1",
                    "idRestaurante": "restaurante-1",
                    "timestamp": 1,
                },
            )
            return await client.post(
                "/pedidos/preparar",
                json={
                    "idPedido": id_pedido,
                    "idRestaurante": "restaurante-1",
                    "timestamp": 2,
                },
            )

    response = run(_post())

    assert response.status_code == 200
    assert response.json()["restaurantePreparou"] is True


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


def test_criar_adm_padrao_recebe_publisher_injetado():
    publisher = object()
    from src.api import _criar_adm_padrao

    adm = _criar_adm_padrao(publisher)

    assert adm.publisher is publisher


def test_criar_adm_padrao_usa_rastreadores_configurados(monkeypatch):
    monkeypatch.setenv("ADM_ID", "adm-1")
    monkeypatch.setenv("ADM_CLUSTER", "adm-1")
    monkeypatch.setenv("ADM_TRACKERS", "rastreador-1, rastreador-2, rastreador-3")
    monkeypatch.setenv(
        "ADM_SUPPORT_URLS",
        "rastreador-3:http://127.0.0.1:9103",
    )
    from src.api import _criar_adm_padrao

    adm = _criar_adm_padrao(None)

    assert adm.servidores_rastreadores == [
        "rastreador-1",
        "rastreador-2",
        "rastreador-3",
    ]
    assert adm.support_urls["rastreador-3"] == "http://127.0.0.1:9103"
