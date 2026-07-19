"""Tests for restaurant broker client."""

from uuid import uuid4

import httpx
import pytest

from src.clients.restaurant_broker import (
    RestaurantBrokerError,
    criar_callback_pedido_para_restaurante,
    preparar_pedido_via_adm,
)


def test_preparar_pedido_via_adm_sucesso(monkeypatch):
    id_pedido = uuid4()
    chamadas = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"idPedido": str(id_pedido), "restaurantePreparou": True}

    class FakeClient:
        def __init__(self, timeout):
            del timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            chamadas.append((url, json))
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    resultado = preparar_pedido_via_adm(
        "http://127.0.0.1:8003",
        "restaurante-1",
        id_pedido,
    )

    assert resultado["restaurantePreparou"] is True
    assert chamadas[0][0] == "http://127.0.0.1:8003/pedidos/preparar"
    assert chamadas[0][1]["idRestaurante"] == "restaurante-1"


def test_preparar_pedido_via_adm_retorna_erro_quando_nao_e_lider(monkeypatch):
    class FakeResponse:
        status_code = 409

        @staticmethod
        def json():
            return {"detail": {"liderAtual": "adm-3", "idServidor": "adm-1"}}

    class FakeClient:
        def __init__(self, timeout):
            del timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            del url, json
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    with pytest.raises(RestaurantBrokerError, match="nao e o lider"):
        preparar_pedido_via_adm(
            "http://127.0.0.1:8001",
            "restaurante-1",
            uuid4(),
        )


def test_callback_restaurante_filtra_e_prepara_pedido(monkeypatch):
    id_pedido = uuid4()
    preparados = []
    callback = criar_callback_pedido_para_restaurante(
        id_restaurante="restaurante-1",
        adm_url="http://127.0.0.1:8003",
    )

    monkeypatch.setattr(
        "src.clients.restaurant_broker.preparar_pedido_via_adm",
        lambda adm_url, id_restaurante, pedido_id: preparados.append(
            (adm_url, id_restaurante, pedido_id)
        )
        or {"idPedido": str(pedido_id)},
    )

    callback(
        {
            "idPedido": str(uuid4()),
            "idRestaurante": "restaurante-2",
            "timestamp": 1,
        }
    )
    callback(
        {
            "idPedido": str(id_pedido),
            "idRestaurante": "restaurante-1",
            "timestamp": 1,
        }
    )

    assert preparados == [("http://127.0.0.1:8003", "restaurante-1", id_pedido)]
