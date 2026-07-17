"""Tests for the SUP HTTP API."""

import asyncio

import httpx
from httpx import ASGITransport, AsyncClient

from src.support_api import create_support_app


def run(coro):
    return asyncio.run(coro)


def test_sup_sync_e_backup():
    app = create_support_app("sup-1", "rastreador-1")

    async def exercitar():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            sync = await client.post(
                "/sync",
                json={
                    "00000000-0000-0000-0000-000000000001": {
                        "idEntregador": "entregador-1",
                        "idServidorRastreador": "rastreador-1",
                        "ultimaLocalizacao": None,
                    }
                },
            )
            assert sync.status_code == 200
            assert sync.json()["pedidos"] == 1

            backup = await client.get("/backup")
            assert backup.status_code == 200
            assert "00000000-0000-0000-0000-000000000001" in backup.json()

            estado = await client.get("/estado")
            assert estado.status_code == 200
            assert estado.json()["pedidosNoBackup"] == 1

    run(exercitar())
