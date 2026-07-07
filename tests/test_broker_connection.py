"""BrokerConnection lifecycle tests."""

import importlib
import sys
from types import SimpleNamespace


class FakeChannel:
    def __init__(self):
        self.is_open = True
        self.is_closed = False


class FakeBlockingConnection:
    instances = []

    def __init__(self, parameters):
        self.parameters = parameters
        self.is_open = True
        self.is_closed = False
        self.channels = []
        FakeBlockingConnection.instances.append(self)

    def channel(self):
        channel = FakeChannel()
        self.channels.append(channel)
        return channel


class FakeConnectionParameters:
    def __init__(self, host, port):
        self.host = host
        self.port = port


def test_connect_reusa_conexao_aberta_quando_canal_fecha(monkeypatch):
    fake_pika = SimpleNamespace(
        BlockingConnection=FakeBlockingConnection,
        ConnectionParameters=FakeConnectionParameters,
        channel=SimpleNamespace(Channel=FakeChannel),
    )
    monkeypatch.setitem(sys.modules, "pika", fake_pika)
    connection_module = importlib.import_module("src.broker.connection")
    connection_module = importlib.reload(connection_module)

    FakeBlockingConnection.instances = []
    broker = connection_module.BrokerConnection()
    broker.connect()
    broker.channel.is_open = False
    broker.channel.is_closed = True

    broker.connect()

    assert len(FakeBlockingConnection.instances) == 1
    assert len(FakeBlockingConnection.instances[0].channels) == 2
