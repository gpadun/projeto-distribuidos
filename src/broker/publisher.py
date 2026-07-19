"""Event publication through RabbitMQ topic exchanges."""

import json
from typing import Any
from uuid import UUID

import pika

from src.broker.connection import BrokerConnection


def _json_default(value: Any) -> str:
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"{value!r} is not JSON serializable")


class Publisher:
    """Publishes event messages such as PedidoDisponivel and EventoLocalizacao."""

    def __init__(self, broker_connection: BrokerConnection):
        self.broker_connection = broker_connection

    def publish(self, exchange: str, routing_key: str, message: dict) -> None:
        """Publish a JSON message to the given topic exchange/routing key."""
        body = json.dumps(message, default=_json_default).encode("utf-8")
        try:
            self._publish_body(exchange, routing_key, body)
        except pika.exceptions.AMQPError:
            self.broker_connection.close()
            self._publish_body(exchange, routing_key, body)

    def _publish_body(self, exchange: str, routing_key: str, body: bytes) -> None:
        channel = self.broker_connection.get_channel()
        channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=pika.DeliveryMode.Persistent,
            ),
        )
