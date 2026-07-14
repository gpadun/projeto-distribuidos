"""Integration tests that require a real RabbitMQ broker."""

import asyncio
import json
import time
from uuid import uuid4

import pika
import pytest

from src.broker.config import BrokerSettings
from src.broker.factory import criar_publisher, criar_subscriber, fechar_publisher, fechar_subscriber
from src.broker.topology import EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL
from src.core.models import CriarPedido
from src.servers.adm_server import ADMServer

pytestmark = pytest.mark.integration


def rabbitmq_disponivel(settings: BrokerSettings) -> bool:
    """Return True when RabbitMQ accepts a TCP/AMQP connection."""
    try:
        connection = pika.BlockingConnection(settings.connection_parameters())
        connection.close()
        return True
    except Exception:
        return False


@pytest.fixture
def broker_settings() -> BrokerSettings:
    """Broker settings for integration tests."""
    settings = BrokerSettings(
        host="127.0.0.1",
        port=5672,
        user="dsid",
        password="dsid123",
        enabled=True,
    )
    if not rabbitmq_disponivel(settings):
        pytest.skip("RabbitMQ nao disponivel em 127.0.0.1:5672")
    return settings


class FilaDeTeste:
    """Temporary queue bound to a topic exchange for integration assertions."""

    def __init__(self, settings: BrokerSettings, exchange: str, routing_key: str):
        self.connection = pika.BlockingConnection(settings.connection_parameters())
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        result = self.channel.queue_declare(queue="", exclusive=True)
        self.queue_name = result.method.queue
        self.channel.queue_bind(exchange=exchange, queue=self.queue_name, routing_key=routing_key)

    def aguardar_mensagem(self, timeout: float = 5.0) -> dict | None:
        """Poll the queue until one JSON message arrives or timeout expires."""
        prazo = time.time() + timeout
        while time.time() < prazo:
            method, _properties, body = self.channel.basic_get(self.queue_name, auto_ack=True)
            if method is not None:
                return json.loads(body.decode("utf-8"))
            time.sleep(0.1)
        return None

    def close(self) -> None:
        if self.connection.is_open:
            self.connection.close()


def _aguardar_mensagem_com_subscriber(
    settings: BrokerSettings,
    exchange: str,
    routing_key: str,
):
    """
    Register a Subscriber callback and poll events in the same thread.

    Avoids start_consuming() in a background thread, which is unsafe with
    pika's BlockingConnection.
    """
    recebidos: list[dict] = []

    subscriber = criar_subscriber(settings)
    assert subscriber is not None

    def callback(payload: dict) -> None:
        recebidos.append(payload)

    subscriber.subscribe(exchange, routing_key, callback)
    time.sleep(0.2)

    def aguardar(timeout: float = 5.0) -> bool:
        prazo = time.time() + timeout
        connection = subscriber.broker_connection.connection
        assert connection is not None
        while time.time() < prazo and not recebidos:
            connection.process_data_events(time_limit=0.2)
        return bool(recebidos)

    return recebidos, aguardar, subscriber


def test_publicar_e_consumir_pedido_disponivel_no_rabbitmq(broker_settings):
    fila = FilaDeTeste(broker_settings, EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL)
    publisher = criar_publisher(broker_settings)
    assert publisher is not None

    try:
        publisher.publish(
            EXCHANGE_PEDIDOS,
            ROUTING_PEDIDO_DISPONIVEL,
            {
                "idPedido": "00000000-0000-0000-0000-000000000001",
                "idRestaurante": "restaurante-1",
                "timestamp": 1,
            },
        )

        mensagem = fila.aguardar_mensagem()
        assert mensagem is not None, "mensagem nao chegou na fila a tempo"
        assert mensagem["idPedido"] == "00000000-0000-0000-0000-000000000001"
        assert mensagem["idRestaurante"] == "restaurante-1"
        assert mensagem["timestamp"] == 1
    finally:
        fechar_publisher(publisher)
        fila.close()


def test_subscriber_recebe_pedido_disponivel_no_rabbitmq(broker_settings):
    recebidos, aguardar, subscriber = _aguardar_mensagem_com_subscriber(
        broker_settings,
        EXCHANGE_PEDIDOS,
        ROUTING_PEDIDO_DISPONIVEL,
    )

    publisher = criar_publisher(broker_settings)
    assert publisher is not None

    try:
        publisher.publish(
            EXCHANGE_PEDIDOS,
            ROUTING_PEDIDO_DISPONIVEL,
            {
                "idPedido": "00000000-0000-0000-0000-000000000002",
                "idRestaurante": "restaurante-2",
                "timestamp": 2,
            },
        )

        assert aguardar(), "Subscriber nao recebeu a mensagem a tempo"
        assert recebidos[0]["idPedido"] == "00000000-0000-0000-0000-000000000002"
        assert recebidos[0]["idRestaurante"] == "restaurante-2"
        assert recebidos[0]["timestamp"] == 2
    finally:
        fechar_publisher(publisher)
        fechar_subscriber(subscriber)


def test_adm_criar_pedido_publica_pedido_disponivel_no_rabbitmq(broker_settings):
    fila = FilaDeTeste(broker_settings, EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL)
    publisher = criar_publisher(broker_settings)
    assert publisher is not None

    id_pedido = uuid4()
    adm = ADMServer(
        id_servidor="adm-3",
        servidores_adm=["adm-1", "adm-2", "adm-3"],
        servidores_rastreadores=["rastreador-1", "rastreador-2"],
        publisher=publisher,
    )
    adm.lider_atual = "adm-3"

    try:
        asyncio.run(
            adm.criar_pedido(
                CriarPedido(
                    idPedido=id_pedido,
                    idCliente="cliente-1",
                    idRestaurante="restaurante-1",
                    timestamp=1,
                )
            )
        )

        mensagem = fila.aguardar_mensagem()
        assert mensagem is not None, "ADM nao publicou PedidoDisponivel no broker"
        assert mensagem["idPedido"] == str(id_pedido)
        assert mensagem["idRestaurante"] == "restaurante-1"
        assert mensagem["timestamp"] == 1
    finally:
        fechar_publisher(publisher)
        fila.close()
