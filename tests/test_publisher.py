import json
from uuid import uuid4

import pika

from src.broker.publisher import Publisher


class FakeChannel:
    def __init__(self, fail_first_publish: bool = False):
        self.fail_first_publish = fail_first_publish
        self.declared = []
        self.published = []

    def exchange_declare(self, **kwargs):
        self.declared.append(kwargs)

    def basic_publish(self, **kwargs):
        if self.fail_first_publish:
            self.fail_first_publish = False
            raise pika.exceptions.AMQPConnectionError("queda temporaria")
        self.published.append(kwargs)


class FakeConnection:
    def __init__(self):
        self.channels = [FakeChannel(fail_first_publish=True), FakeChannel()]
        self.closed = 0

    def get_channel(self):
        return self.channels[min(self.closed, len(self.channels) - 1)]

    def close(self):
        self.closed += 1


def test_publisher_reconecta_e_tenta_novamente_apos_falha_amqp():
    connection = FakeConnection()
    publisher = Publisher(connection)

    publisher.publish("pedidos", "pedido.disponivel", {"idPedido": uuid4()})

    assert connection.closed == 1
    assert connection.channels[1].declared == [
        {"exchange": "pedidos", "exchange_type": "topic", "durable": True}
    ]
    published = connection.channels[1].published[0]
    assert published["exchange"] == "pedidos"
    assert published["routing_key"] == "pedido.disponivel"
    assert json.loads(published["body"].decode("utf-8"))["idPedido"]
