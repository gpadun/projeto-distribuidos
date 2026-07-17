"""RabbitMQ topic exchanges and routing keys used by the project."""

from uuid import UUID

EXCHANGE_PEDIDOS = "pedidos"
EXCHANGE_RASTREIO = "rastreio"
EXCHANGE_INFRA = "infra"
EXCHANGE_LOCALIZACAO = "localizacao"

ROUTING_PEDIDO_DISPONIVEL = "pedido.disponivel"


def routing_entrega_confirmada(id_pedido: UUID | str) -> str:
    """Routing key for EntregaConfirmada events."""
    return f"pedido.{id_pedido}.entrega_confirmada"


def routing_roteamento(id_servidor_rastreador: str) -> str:
    """Routing key for AtualizacaoRoteamento directed to one tracker."""
    return f"roteamento.{id_servidor_rastreador}"


def routing_localizacao(id_pedido: UUID | str) -> str:
    """Routing key for EventoLocalizacao consumed bt customers."""
    return f"pedido.{id_pedido}"


def routing_desconexao(id_pedido: UUID | str) -> str:
    """Routing key for driver disconnection notifications."""
    return f"pedido.{id_pedido}.desconexao"


def routing_localizacao_para_rastreador(id_servidor_rastreador: str) -> str:
    """Routing key for LocalizacaoEntregadore directed to one tracker."""
    return f"rastreador.{id_servidor_rastreador}"