"""BrokerConnection lifecycle tests."""

from types import SimpleNamespace

import src.broker.connection as connection_module
from src.broker.config import BrokerSettings


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


class FakePlainCredentials:
    def __init__(self, username, password):
        self.username = username
        self.password = password


class FakeConnectionParameters:
    def __init__(self, host, port, credentials=None):
        self.host = host
        self.port = port
        self.credentials = credentials


def test_connect_reusa_conexao_aberta_quando_canal_fecha(monkeypatch):
    fake_pika = SimpleNamespace(
        BlockingConnection=FakeBlockingConnection,
        ConnectionParameters=FakeConnectionParameters,
        PlainCredentials=FakePlainCredentials,
        channel=SimpleNamespace(Channel=FakeChannel),
    )
    monkeypatch.setattr(connection_module, "pika", fake_pika)

    FakeBlockingConnection.instances = []
    settings = BrokerSettings(
        host="localhost",
        port=5672,
        user="dsid",
        password="dsid123",
        enabled=True,
    )
    broker = connection_module.BrokerConnection(settings=settings)
    broker.connect()
    broker.channel.is_open = False
    broker.channel.is_closed = True

    broker.connect()

    assert len(FakeBlockingConnection.instances) == 1
    assert len(FakeBlockingConnection.instances[0].channels) == 2
    assert FakeBlockingConnection.instances[0].parameters.credentials.username == "dsid"
