"""Factory helpers to create broker clients from centralized settings."""

import logging

from src.broker.config import BrokerSettings
from src.broker.connection import BrokerConnection
from src.broker.publisher import Publisher
from src.broker.subscriber import Subscriber

logger = logging.getLogger(__name__)


class BrokerUnavailableError(RuntimeError):
    """Raised when RabbitMQ is enabled but cannot be reached."""


def criar_broker_connection(settings: BrokerSettings | None = None) -> BrokerConnection:
    """Create a broker connection wrapper without opening it yet."""
    return BrokerConnection(settings or BrokerSettings.from_env())


def _conectar_ou_falhar(connection: BrokerConnection, settings: BrokerSettings) -> None:
    """Open the broker connection or raise a clear startup error."""
    try:
        connection.connect()
    except Exception as exc:
        mensagem = (
            "nao foi possivel conectar ao RabbitMQ em "
            f"{settings.host}:{settings.port} com usuario '{settings.user}'. "
            "verifique se o container esta rodando com 'docker compose up -d'"
        )
        logger.error(mensagem)
        raise BrokerUnavailableError(mensagem) from exc
    

def criar_publisher(settings: BrokerSettings | None = None) -> Publisher | None:
    """
    Create a real Publisher when RabbitMQ is enabled.
    
    Returns None when RABBITMQ_ENABLED=0 so tests and local runs can stay in-memory without requiring Docker.
    """
    config = settings or BrokerSettings.from_env()
    if not config.enabled:
        logger.info("RabbitMQ desabilitado (RABBITMQ_ENABLED=0); publisher nao sera criado")
        return None
    
    connection = criar_broker_connection(config)
    _conectar_ou_falhar(connection, config)
    logger.info(
        "Publisher RabbitMQ conectado em %s:%s",
        config.host,
        config.port,
    )
    return Publisher(connection)


def criar_subscriber(settings: BrokerSettings | None = None) -> Subscriber | None:
    """
    Create a real Subscriber when RabbitMQ is enabled.
    
    Same enabled/disabled behavior as criar_publisher()
    """
    config = settings or BrokerSettings.from_env()
    if not config.enabled:
        logger.info("RabbitMQ desabilitado (RABBITMQ_ENABLED=0); subscriber nao sera criado")
        return None
    
    connection = criar_broker_connection(config)
    _conectar_ou_falhar(connection, config)
    logger.info(
        "Subscriber RabbitMQ conectado em %s:%s",
        config.host,
        config.port,
    )
    return Subscriber(connection)


def fechar_publisher(publisher: Publisher | None) -> None:
    """Close the underlying RabbitMQ connection owned by a publisher."""
    if publisher is None:
        return
    publisher.broker_connection.close()


def fechar_subscriber(subscriber: Subscriber | None) -> None:
    """Close the underlying RabbitMQ connection owned by a subscriber."""
    if subscriber is None:
        return
    connection = subscriber.broker_connection
    channel = connection.channel
    if channel is not None and channel.is_open:
        try:
            channel.stop_consuming()
        except Exception:
            pass
    connection.close()
