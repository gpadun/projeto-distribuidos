"""Tests for driver broker client."""

import threading
import time
from uuid import uuid4

import httpx
import pytest

from src.broker.config import BrokerSettings
from src.clients.driver_broker import (
    DriverBrokerError,
    _publicar_localizacoes_periodicas,
    aceitar_pedido_via_adm,
    criar_callback_entrega_confirmada,
    criar_callback_pedido_disponivel,
    criar_callback_rastreador_atualizado,
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
    monkeypatch.setattr(
        "src.clients.driver_broker.resolver_adm_lider_url",
        lambda **kwargs: "http://127.0.0.1:8003",
    )
    monkeypatch.setattr(
        "src.clients.driver_broker.carregar_adm_urls",
        lambda: ["http://127.0.0.1:8003"],
    )

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
    monkeypatch.setattr(
        "src.clients.driver_broker.resolver_adm_lider_url",
        lambda **kwargs: "http://127.0.0.1:8001",
    )
    monkeypatch.setattr(
        "src.clients.driver_broker.carregar_adm_urls",
        lambda: ["http://127.0.0.1:8001"],
    )

    with pytest.raises(DriverBrokerError, match="nao e o lider"):
        aceitar_pedido_via_adm(
            "http://127.0.0.1:8001",
            "entregador-1",
            uuid4(),
        )


def test_aceitar_pedido_via_adm_tenta_outro_adm_quando_lider_caiu(monkeypatch):
    id_pedido = uuid4()
    chamadas = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "idPedido": str(id_pedido),
                "servidorRastreadorResponsavel": "rastreador-2",
            }

    class FakeClient:
        def __init__(self, timeout):
            del timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            chamadas.append(url)
            if ":8003" in url:
                raise httpx.ConnectError("adm-3 offline")
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(
        "src.clients.driver_broker.resolver_adm_lider_url",
        lambda **kwargs: "http://127.0.0.1:8003",
    )
    monkeypatch.setattr(
        "src.clients.driver_broker.carregar_adm_urls",
        lambda: [
            "http://127.0.0.1:8001",
            "http://127.0.0.1:8002",
            "http://127.0.0.1:8003",
        ],
    )

    resultado = aceitar_pedido_via_adm(
        "http://127.0.0.1:8003",
        "entregador-1",
        id_pedido,
    )

    assert resultado["servidorRastreadorResponsavel"] == "rastreador-2"
    assert any(":8002" in url or ":8001" in url for url in chamadas)


def test_callback_imprime_e_aceita_pedido(monkeypatch, capsys):
    id_pedido = uuid4()
    aceitos = []
    threads = []

    monkeypatch.setattr(
        "src.clients.driver_broker.aceitar_pedido_via_adm",
        lambda adm_url, id_entregador, pedido_id, **kwargs: aceitos.append(
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
    rastreador_por_pedido = {}
    callback = criar_callback_pedido_disponivel(
        id_entregador="entregador-1",
        adm_url="http://127.0.0.1:8003",
        aceitar_automatico=True,
        broker_settings=settings,
        parar_gps={},
        rastreador_por_pedido=rastreador_por_pedido,
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
    assert rastreador_por_pedido[id_pedido] == "rastreador-2"
    assert "pedido disponivel" in capsys.readouterr().out


def test_callback_rastreador_atualizado():
    id_pedido = uuid4()
    rastreador_por_pedido = {id_pedido: "rastreador-1"}
    parar_gps = {id_pedido: threading.Event()}

    callback = criar_callback_rastreador_atualizado(rastreador_por_pedido, parar_gps)
    callback(
        {
            "idPedido": str(id_pedido),
            "idServidorRastreador": "rastreador-2",
            "idEntregador": "entregador-1",
            "timestamp": 1,
        }
    )

    assert rastreador_por_pedido[id_pedido] == "rastreador-2"


def test_callback_rastreador_atualizado_ignora_pedido_confirmado():
    id_pedido = uuid4()
    rastreador_por_pedido = {}
    parar = threading.Event()
    parar.set()
    parar_gps = {id_pedido: parar}

    callback = criar_callback_rastreador_atualizado(rastreador_por_pedido, parar_gps)
    callback(
        {
            "idPedido": str(id_pedido),
            "idServidorRastreador": "rastreador-2",
            "idEntregador": "entregador-1",
            "timestamp": 1,
        }
    )

    assert rastreador_por_pedido == {}


def test_publicar_localizacoes_usa_rastreador_atualizado(monkeypatch):
    id_pedido = uuid4()
    publicacoes = []
    parar = threading.Event()
    rastreador_por_pedido = {id_pedido: "rastreador-1"}

    class FakePublisher:
        def publish(self, exchange, routing_key, message):
            publicacoes.append(routing_key)

    monkeypatch.setattr(
        "src.clients.driver_broker.criar_publisher",
        lambda settings: FakePublisher(),
    )
    monkeypatch.setattr(
        "src.clients.driver_broker.fechar_publisher",
        lambda publisher: None,
    )

    thread = threading.Thread(
        target=_publicar_localizacoes_periodicas,
        args=(
            "entregador-1",
            id_pedido,
            0.05,
            BrokerSettings(enabled=True),
            parar,
            rastreador_por_pedido,
        ),
        daemon=True,
    )
    thread.start()
    time.sleep(0.07)
    rastreador_por_pedido[id_pedido] = "rastreador-2"
    time.sleep(0.07)
    parar.set()
    thread.join(timeout=1)

    assert "rastreador.rastreador-1" in publicacoes
    assert "rastreador.rastreador-2" in publicacoes


def test_callback_entrega_confirmada_para_gps():
    id_pedido = uuid4()
    parar_gps = {id_pedido: threading.Event()}
    rastreador_por_pedido = {id_pedido: "rastreador-1"}

    callback = criar_callback_entrega_confirmada(parar_gps, rastreador_por_pedido)
    callback({"idPedido": str(id_pedido), "timestamp": 1})

    assert parar_gps[id_pedido].is_set()
    assert id_pedido not in rastreador_por_pedido


def test_publicar_localizacoes_para_quando_entrega_confirmada(monkeypatch):
    id_pedido = uuid4()
    publicacoes = []
    parar = threading.Event()

    class FakePublisher:
        def publish(self, exchange, routing_key, message):
            del exchange, routing_key, message
            publicacoes.append(1)

    monkeypatch.setattr(
        "src.clients.driver_broker.criar_publisher",
        lambda settings: FakePublisher(),
    )
    monkeypatch.setattr(
        "src.clients.driver_broker.fechar_publisher",
        lambda publisher: None,
    )

    thread = threading.Thread(
        target=_publicar_localizacoes_periodicas,
        args=(
            "entregador-1",
            id_pedido,
            0.05,
            BrokerSettings(enabled=True),
            parar,
            {id_pedido: "rastreador-1"},
        ),
        daemon=True,
    )
    thread.start()
    time.sleep(0.12)
    parar.set()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert len(publicacoes) >= 1
    assert len(publicacoes) <= 4