"""Tests for broker factory helpers."""

import pytest

from src.broker.config import BrokerSettings
from src.broker.factory import (
    BrokerUnavailableError,
    criar_publisher,
    criar_subscriber,
    fechar_publisher,
)


class FakeBrokerConnection:
    def __init__(self, settings):
        self.settings = settings
        self.connected = False
        self.closed = False

    def connect(self) -> None:
        if getattr(self.settings, "should_fail", False):
            raise ConnectionError("broker offline")
        self.connected = True

    def close(self) -> None:
        self.closed = True


class FakePublisher:
    def __init__(self, broker_connection):
        self.broker_connection = broker_connection


class FakeSubscriber:
    def __init__(self, broker_connection):
        self.broker_connection = broker_connection


def test_criar_publisher_retorna_none_quando_desabilitado(monkeypatch):
    settings = BrokerSettings(enabled=False)

    publisher = criar_publisher(settings)

    assert publisher is None


def test_criar_subscriber_retorna_none_quando_desabilitado(monkeypatch):
    settings = BrokerSettings(enabled=False)

    subscriber = criar_subscriber(settings)

    assert subscriber is None


def test_criar_publisher_conecta_quando_habilitado(monkeypatch):
    conexoes: list[FakeBrokerConnection] = []

    def fake_criar_connection(settings):
        conexao = FakeBrokerConnection(settings)
        conexoes.append(conexao)
        return conexao

    monkeypatch.setattr(
        "src.broker.factory.criar_broker_connection",
        fake_criar_connection,
    )
    monkeypatch.setattr("src.broker.factory.Publisher", FakePublisher)

    settings = BrokerSettings(enabled=True)
    publisher = criar_publisher(settings)

    assert publisher is not None
    assert len(conexoes) == 1
    assert conexoes[0].connected is True
    assert publisher.broker_connection is conexoes[0]


def test_criar_publisher_levanta_erro_quando_broker_indisponivel(monkeypatch):
    class SettingsComFalha(BrokerSettings):
        should_fail = True

    def fake_criar_connection(settings):
        return FakeBrokerConnection(settings)

    monkeypatch.setattr(
        "src.broker.factory.criar_broker_connection",
        fake_criar_connection,
    )

    settings = SettingsComFalha(enabled=True)

    with pytest.raises(BrokerUnavailableError, match="nao foi possivel conectar ao RabbitMQ"):
        criar_publisher(settings)


def test_fechar_publisher_fecha_conexao():
    conexao = FakeBrokerConnection(BrokerSettings(enabled=True))
    publisher = FakePublisher(conexao)

    fechar_publisher(publisher)

    assert conexao.closed is True


def test_fechar_publisher_aceita_none():
    fechar_publisher(None)