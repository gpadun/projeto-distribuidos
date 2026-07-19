"""Subscriber callback acknowledgement tests."""

from types import SimpleNamespace

from src.broker.subscriber import Subscriber


class FakeConnection:
    def __init__(self):
        self.channel = FakeChannel()

    def get_channel(self):
        return self.channel


class FakeChannel:
    def __init__(self):
        self.callback = None
        self.acked = []
        self.nacked = []
        self.stopped = False

    def exchange_declare(self, exchange, exchange_type, durable):
        pass

    def queue_declare(self, queue, exclusive):
        return SimpleNamespace(method=SimpleNamespace(queue="fila-teste"))

    def queue_bind(self, exchange, queue, routing_key):
        pass

    def basic_consume(self, queue, on_message_callback):
        self.callback = on_message_callback

    def start_consuming(self):
        pass

    def stop_consuming(self):
        self.stopped = True

    def basic_ack(self, delivery_tag):
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacked.append((delivery_tag, requeue))


def test_subscriber_ack_em_mensagem_valida():
    connection = FakeConnection()
    subscriber = Subscriber(connection)
    mensagens = []
    subscriber.subscribe("rastreio", "pedido.1", mensagens.append)

    method = SimpleNamespace(delivery_tag=1)
    connection.channel.callback(connection.channel, method, None, b'{"ok": true}')

    assert mensagens == [{"ok": True}]
    assert connection.channel.acked == [1]
    assert connection.channel.nacked == []


def test_subscriber_nack_sem_requeue_em_payload_invalido():
    connection = FakeConnection()
    subscriber = Subscriber(connection)
    subscriber.subscribe("rastreio", "pedido.1", lambda payload: payload)

    method = SimpleNamespace(delivery_tag=2)
    connection.channel.callback(connection.channel, method, None, b'{"quebrado":')

    assert connection.channel.acked == []
    assert connection.channel.nacked == [(2, False)]


def test_subscriber_nack_quando_json_nao_e_objeto():
    connection = FakeConnection()
    subscriber = Subscriber(connection)
    subscriber.subscribe("rastreio", "pedido.1", lambda payload: payload)

    method = SimpleNamespace(delivery_tag=3)
    connection.channel.callback(connection.channel, method, None, b'["lista-valida-mas-invalida"]')

    assert connection.channel.acked == []
    assert connection.channel.nacked == [(3, False)]


def test_subscriber_stop_consuming():
    connection = FakeConnection()
    subscriber = Subscriber(connection)

    subscriber.stop_consuming()

    assert connection.channel.stopped is True
