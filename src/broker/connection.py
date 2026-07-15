"""RabbitMQ connection management."""

import pika

from src.broker.config import BrokerSettings


class BrokerConnection:
    """Owns a RabbitMQ blocking connection and channel."""

    def __init__(self, settings: BrokerSettings | None = None):
        self.settings = settings or BrokerSettings.from_env()
        self.connection: pika.BlockingConnection | None = None
        self.channel: pika.channel.Channel | None = None


    @property
    def host(self) -> str:
        return self.settings.host


    @property
    def port(self) -> int:
        return self.settings.port
    

    def connect(self) -> None:
        """Open the connection and channel if they are not already open."""
        if (
            self.connection
            and self.connection.is_open
            and self.channel
            and self.channel.is_open
        ):
            return

        if self.connection is None or self.connection.is_closed:
            parameters = self.settings.connection_parameters()
            self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()


    def get_channel(self) -> pika.channel.Channel:
        """Return an active channel, connecting lazily when needed."""
        if self.channel is None or self.channel.is_closed:
            self.connect()

        assert self.channel is not None
        return self.channel


    def close(self) -> None:
        """Close the broker connection."""
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
            except Exception:
                pass
        self.connection = None
        self.channel = None
