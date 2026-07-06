"""Gerenciamento da conexão com o Message Broker (RabbitMQ via pika)."""

import pika


class BrokerConnection:
    """Encapsula o ciclo de vida de uma conexão com o RabbitMQ."""

    def __init__(self, host: str, port: int = 5672):
        """Armazena os parâmetros de conexão com o broker."""
        raise NotImplementedError

    def connect(self) -> None:
        """Estabelece a conexão e abre um canal com o broker."""
        raise NotImplementedError

    def get_channel(self) -> pika.channel.Channel:
        """Retorna o canal ativo da conexão."""
        raise NotImplementedError

    def close(self) -> None:
        """Encerra a conexão com o broker."""
        raise NotImplementedError
