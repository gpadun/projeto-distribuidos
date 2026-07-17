"""Tests for driver broker client."""

from uuid import uuid4

import httpx
import pytest

from src.broker.config import BrokerSettings
from src.clients.driver_broker import (
    DriverBrokerError,
    aceitar_pedido_via_adm,
    criar_callback_pedido_disponivel,
    parse_pedido_disponivel,
)


def test_parse_pedido_disponivel_valida_payload():
    id_pedido = uuid4()
    evento = parse_pedido_disponivel(
        {
            "idPedido": str(id_pedido),
            "idRestaurante": "restaurante-1",
            "timestamp": 1,
        }
    )

    assert evento.idPedido == id_pedido
    assert evento.idRestaurante == "restaurante-1"
    assert evento.timestamp == 1


def test_aceitar_pedido_via_adm_sucesso(monkeypatch):
    id_pedido = uuid4()
    chamadas = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "idPedido": str(id_pedido),
                "servidorRastreadorResponsavel": "rastreador-1",
            }

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

    resultado = aceitar_pedido_via_adm(
        "http://127.0.0.1:8003",
        "entregador-1",
        id_pedido,
    )

    assert resultado["servidorRastreadorResponsavel"] == "rastreador-1"
    assert chamadas[0][0] == "http://127.0.0.1:8003/pedidos/aceitar"
    assert chamadas[0][1]["idEntregador"] == "entregador-1"


def test_aceitar_pedido_via_adm_retorna_erro_quando_nao_e_lider(monkeypatch):
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

    with pytest.raises(DriverBrokerError, match="nao e o lider"):
        aceitar_pedido_via_adm(
            "http://127.0.0.1:8001",
            "entregador-1",
            uuid4(),
        )


def test_callback_imprime_e_aceita_pedido(monkeypatch, capsys):
    id_pedido = uuid4()
    aceitos = []
    threads = []

    monkeypatch.setattr(
        "src.clients.driver_broker.aceitar_pedido_via_adm",
        lambda adm_url, id_entregador, pedido_id: aceitos.append(
            (adm_url, id_entregador, pedido_id)
        )
        or {"idPedido": str(pedido_id), "servidorRastreadorResponsavel": "rastreador-2"},
    )

    class FakeThread:
        def __init__(self, target, args=(), daemon=False):
            del target, args, daemon

        def start(self):
            threads.append(self)

    monkeypatch.setattr("src.clients.driver_broker.threading.Thread", FakeThread)

    settings = BrokerSettings(enabled=True)
    callback = criar_callback_pedido_disponivel(
        id_entregador="entregador-1",
        adm_url="http://127.0.0.1:8003",
        aceitar_automatico=True,
        broker_settings=settings,
    )
    callback(
        {
            "idPedido": str(id_pedido),
            "idRestaurante": "restaurante-1",
            "timestamp": 1,
        }
    )

    assert len(aceitos) == 1
    assert aceitos[0][2] == id_pedido
    assert len(threads) == 1
    assert "pedido disponivel" in capsys.readouterr().out