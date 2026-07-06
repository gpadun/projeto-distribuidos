"""Publicação de mensagens de evento no Message Broker (padrão Publish-Subscribe)."""

from src.broker.connection import BrokerConnection


class Publisher:
    """Publica mensagens de evento (ex: PedidoDisponivel, LocalizacaoEntregador)."""

    def __init__(self, broker_connection: BrokerConnection):
        """Associa o publicador a uma conexão ativa com o broker."""
        raise NotImplementedError

    def publish(self, exchange: str, routing_key: str, message: dict) -> None:
        """Publica `message` no `exchange`/`routing_key` informados."""
        raise NotImplementedError
