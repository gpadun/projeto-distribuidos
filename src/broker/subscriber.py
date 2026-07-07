"""Topic subscriptions for RabbitMQ publish-subscribe events."""

import json
from collections.abc import Callable
from typing import Any


class Subscriber:
    """Consumes events and dispatches decoded JSON payloads to callbacks."""

    def __init__(self, broker_connection: Any):
        self.broker_connection = broker_connection
        self._queue_names: list[str] = []

    def subscribe(self, exchange: str, routing_key: str, callback: Callable[[dict], None]) -> None:
        """Subscribe to a topic and call `callback` for every received message."""
        channel = self.broker_connection.get_channel()
        channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        result = channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue
        channel.queue_bind(exchange=exchange, queue=queue_name, routing_key=routing_key)
        self._queue_names.append(queue_name)

        def _on_message(ch, method, properties, body) -> None:
            del properties
            try:
                payload = json.loads(body.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("payload must be a JSON object")
                callback(payload)
            except Exception:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=queue_name, on_message_callback=_on_message)

    def start_consuming(self) -> None:
        """Start RabbitMQ's blocking consume loop."""
        self.broker_connection.get_channel().start_consuming()
