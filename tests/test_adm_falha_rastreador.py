"""Tests for ADM tracker failure detection and redistribution."""

import asyncio
from time import time
from uuid import uuid4

import httpx

from src.core.models import AceitarPedido, CriarPedido, KeepAlive, TipoServidor
from src.servers.adm_server import ADMServer
from src.servers.support_server import SupportServer


class RecordingPublisher:
    def __init__(self):
        self.messages = []

    def publish(self, exchange: str, routing_key: str, message: dict) -> None:
        self.messages.append(
            {"exchange": exchange, "routing_key": routing_key, "message": message}
        )


def run(coro):
    return asyncio.run(coro)


def _registrar_rastreadores_ativos(adm: ADMServer) -> None:
    for id_rastreador in adm.servidores_rastreadores:
        run(
            adm.processar_keepalive(
                KeepAlive(
                    idServidor=id_rastreador,
                    tipoServidor=TipoServidor.RASTREADOR,
                    timestamp=1,
                )
            )
        )


def test_detectar_falha_publica_id_entregador_e_rastreador_atualizado():
    publisher = RecordingPublisher()
    id_pedido = uuid4()
    adm = ADMServer(
        "adm-3",
        ["rastreador-1", "rastreador-2"],
        publisher=publisher,
        servidores_adm=["adm-1", "adm-2", "adm-3"],
    )
    _registrar_rastreadores_ativos(adm)

    run(
        adm.criar_pedido(
            CriarPedido(
                idPedido=id_pedido,
                idCliente="cliente-1",
                idRestaurante="restaurante-1",
                timestamp=1,
            )
        )
    )
    run(
        adm.aceitar_pedido(
            AceitarPedido(
                idPedido=id_pedido,
                idEntregador="entregador-1",
                timestamp=2,
            )
        )
    )

    servidor_atual = adm.mapa_pedido_servidor[id_pedido]
    novo_servidor = (
        "rastreador-2" if servidor_atual == "rastreador-1" else "rastreador-1"
    )

    redistribuidos = run(adm.detectar_falha_servidor_rastreador(servidor_atual))

    assert redistribuidos[id_pedido] == novo_servidor
    infra_msgs = [m for m in publisher.messages if m["exchange"] == "infra"]
    pedido_msgs = [m for m in publisher.messages if m["exchange"] == "pedidos"]

    assert any(
        m["routing_key"] == f"roteamento.{novo_servidor}"
        and m["message"]["idEntregador"] == "entregador-1"
        for m in infra_msgs
    )
    assert any(
        m["routing_key"] == f"pedido.{id_pedido}.rastreador_atualizado"
        for m in pedido_msgs
    )


def test_ciclo_monitoramento_redistribui_rastreador_expirado():
    publisher = RecordingPublisher()
    id_pedido = uuid4()
    adm = ADMServer(
        "adm-3",
        ["rastreador-1", "rastreador-2"],
        publisher=publisher,
        servidores_adm=["adm-1", "adm-2", "adm-3"],
        heartbeat_timeout=5,
    )
    adm.lider_atual = "adm-3"
    _registrar_rastreadores_ativos(adm)

    run(
        adm.criar_pedido(
            CriarPedido(
                idPedido=id_pedido,
                idCliente="cliente-1",
                idRestaurante="restaurante-1",
                timestamp=1,
            )
        )
    )
    run(
        adm.aceitar_pedido(
            AceitarPedido(
                idPedido=id_pedido,
                idEntregador="entregador-1",
                timestamp=2,
            )
        )
    )
    servidor_atual = adm.mapa_pedido_servidor[id_pedido]
    novo_servidor = (
        "rastreador-2" if servidor_atual == "rastreador-1" else "rastreador-1"
    )
    adm.ultimo_keepalive[servidor_atual] = time() - 10

    run(adm.executar_ciclo_monitoramento())

    assert adm.mapa_pedido_servidor[id_pedido] == novo_servidor
    assert servidor_atual not in adm.servidores_rastreadores_ativos


def test_buscar_backup_sup_via_http(monkeypatch):
    adm = ADMServer(
        "adm-1",
        ["rastreador-1"],
        support_urls={"rastreador-1": "http://127.0.0.1:9101"},
    )
    backup_esperado = {
        str(uuid4()): {
            "idEntregador": "entregador-1",
            "idServidorRastreador": "rastreador-1",
            "ultimaLocalizacao": None,
        }
    }

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return backup_esperado

    class FakeClient:
        def __init__(self, timeout):
            del timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            assert url == "http://127.0.0.1:9101/backup"
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    backup = run(adm._buscar_backup_sup("rastreador-1"))

    assert backup == backup_esperado


def test_detectar_falha_usa_backup_do_sup_em_memoria():
    support = SupportServer("sup-1", "rastreador-1")
    id_pedido = uuid4()
    support.rastreios = {
        str(id_pedido): {
            "idEntregador": "entregador-1",
            "idServidorRastreador": "rastreador-1",
            "ultimaLocalizacao": None,
        }
    }

    publisher = RecordingPublisher()
    adm = ADMServer(
        "adm-1",
        ["rastreador-1", "rastreador-2"],
        publisher=publisher,
        support_servers={"rastreador-1": support},
    )
    adm.mapa_pedido_servidor[id_pedido] = "rastreador-1"
    adm.servidores_rastreadores_ativos.update({"rastreador-1", "rastreador-2"})

    redistribuidos = run(adm.detectar_falha_servidor_rastreador("rastreador-1"))

    assert redistribuidos[id_pedido] == "rastreador-2"
