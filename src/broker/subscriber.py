"""Assinatura de tópicos de evento no Message Broker (padrão Publish-Subscribe)."""

from collections.abc import Callable

from src.broker.connection import BrokerConnection


class Subscriber:
    """Assina eventos (ex: EventoLocalizacao, PedidoDisponivel) e despacha callbacks."""

    def __init__(self, broker_connection: BrokerConnection):
        """Associa o assinante a uma conexão ativa com o broker."""
        raise NotImplementedError

    def subscribe(self, exchange: str, routing_key: str, callback: Callable[[dict], None]) -> None:
        """Registra `callback` para mensagens recebidas em `exchange`/`routing_key`."""
        raise NotImplementedError

    def start_consuming(self) -> None:
        """Inicia o loop de consumo de mensagens (bloqueante)."""
        raise NotImplementedError
