"""Centralized RabbitMQ configuration from environment variables."""

import os
from dataclasses import dataclass

import pika


@dataclass(frozen=True)
class BrokerSettings:
    """Connection settings shared by Publisher, Subscriber and BrokerConnection."""

    host: str = "localhost"
    port: int = 5672
    user: str = "dsid"
    password: str = "dsid123"
    enabled: bool = False


    @classmethod
    def from_env(cls) -> "BrokerSettings":
        """Load broker settings from environment variables."""
        return cls(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            user=os.getenv("RABBITMQ_USER", "dsid"),
            password=os.getenv("RABBITMQ_PASSWORD", "dsid123"),
            enabled=os.getenv("RABBITMQ_ENABLED", "0") == "1",
        )
    
    def connection_parameters(self) -> pika.ConnectionParameters:
        """Build pika connection parameters with credentials."""
        credentials = pika.PlainCredentials(self.user, self.password)
        return pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials
        )
