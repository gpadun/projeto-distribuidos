"""Tests for centralized broker configuration."""

import pika

from src.broker.config import BrokerSettings


def test_broker_settings_defaults():
    settings = BrokerSettings()

    assert settings.host == "localhost"
    assert settings.port == 5672
    assert settings.user == "dsid"
    assert settings.password == "dsid123"
    assert settings.enabled is False


def test_broker_settings_from_env(monkeypatch):
    monkeypatch.setenv("RABBITMQ_HOST", "broker.local")
    monkeypatch.setenv("RABBITMQ_PORT", "5673")
    monkeypatch.setenv("RABBITMQ_USER", "user-test")
    monkeypatch.setenv("RABBITMQ_PASSWORD", "secret")
    monkeypatch.setenv("RABBITMQ_ENABLED", "1")

    settings = BrokerSettings.from_env()

    assert settings.host == "broker.local"
    assert settings.port == 5673
    assert settings.user == "user-test"
    assert settings.password == "secret"
    assert settings.enabled is True


def test_broker_settings_connection_parameters_usa_credenciais():
    settings = BrokerSettings(user="dsid", password="dsid123")

    parameters = settings.connection_parameters()

    assert isinstance(parameters, pika.ConnectionParameters)
    assert parameters.credentials.username == "dsid"
    assert parameters.credentials.password == "dsid123"