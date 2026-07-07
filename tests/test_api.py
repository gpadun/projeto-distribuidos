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
