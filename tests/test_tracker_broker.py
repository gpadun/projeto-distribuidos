from uuid import uuid4
import asyncio

from src.core.models import AtualizacaoRoteamento, LocalizacaoEntregador
from src.servers.tracker_server import TrackerServer


class RecordingPublisher:
    def __init__(self):
        self.messages = []

    def publish(self, exchange, routing_key, message):
        self.messages.append((exchange, routing_key, message))


def run(coro):
    return asyncio.run(coro)


def test_rastreador_registra_pedido_via_roteamento():
    tracker = TrackerServer("rastreador-1")
    id_pedido = uuid4()

    run(
        tracker.processar_atualizacao_roteamento(
            AtualizacaoRoteamento(
                idPedido=id_pedido,
                idServidorRastreador="rastreador-1",
                idEntregador="entregador-1",
                timestamp=1,
            )
        )
    )

    assert tracker.entregadores_por_pedido[id_pedido] == "entregador-1"


def test_rastreador_publica_evento_localizacao():
    publisher = RecordingPublisher()
    tracker = TrackerServer("rastreador-1", publisher=publisher)
    id_pedido = uuid4()

    run(tracker.registrar_entregador("entregador-1", id_pedido))
    run(
        tracker.processar_localizacao_entregador(
            LocalizacaoEntregador(
                idEntregador="entregador-1",
                idPedido=id_pedido,
                latitude=-23.55,
                longitude=-46.63,
                timestamp=2,
            )
        )
    )

    assert len(publisher.messages) == 1
    assert publisher.messages[0][0] == "rastreio"