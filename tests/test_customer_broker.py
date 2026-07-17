"""Tests for customer broker client."""

from uuid import uuid4

import httpx
import pytest

from src.clients.customer_broker import (
    CustomerBrokerError,
    criar_callback_localizacao,
    criar_pedido_via_adm,
    parse_evento_localizacao,
)


def test_parse_evento_localizacao_valida_payload():
    id_pedido = uuid4()
    evento = parse_evento_localizacao(
        {
            "idPedido": str(id_pedido),
            "latitude": -23.55,
            "longitude": -46.63,
            "timestamp": 10,
        }
    )

    assert evento.idPedido == id_pedido
    assert evento.latitude == -23.55
    assert evento.longitude == -46.63


def test_criar_pedido_via_adm_sucesso(monkeypatch):
    id_pedido = uuid4()
    chamadas = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"idPedido": str(id_pedido)}

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

    resultado = criar_pedido_via_adm(
        "http://127.0.0.1:8003",
        "cliente-1",
        "restaurante-1",
        id_pedido,
    )

    assert resultado == id_pedido
    assert chamadas[0][0] == "http://127.0.0.1:8003/pedidos"
    assert chamadas[0][1]["idCliente"] == "cliente-1"


def test_criar_pedido_via_adm_retorna_erro_quando_nao_e_lider(monkeypatch):
    class FakeResponse:
        status_code = 409

        @staticmethod
        def json():
            return {"detail": {"liderAtual": "adm-3"}}

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

    with pytest.raises(CustomerBrokerError, match="nao e o lider"):
        criar_pedido_via_adm(
            "http://127.0.0.1:8001",
            "cliente-1",
            "restaurante-1",
        )


def test_callback_localizacao_imprime_evento(capsys):
    id_pedido = uuid4()
    callback = criar_callback_localizacao("cliente-1")
    callback(
        {
            "idPedido": str(id_pedido),
            "latitude": -23.55,
            "longitude": -46.63,
            "timestamp": 10,
        }
    )

    saida = capsys.readouterr().out
    assert "localizacao" in saida
    assert str(id_pedido) in saida