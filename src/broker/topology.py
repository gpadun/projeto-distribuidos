"""RabbitMQ topic exchanges and routing keys used by the project."""

from uuid import UUID

EXCHANGE_PEDIDOS = "pedidos"
EXCHANGE_RASTREIO = "rastreio"
EXCHANGE_INFRA = "infra"
EXCHANGE_LOCALIZACAO = "localizacao"

ROUTING_PEDIDO_DISPONIVEL = "pedido.disponivel"
ROUTING_ENTREGA_CONFIRMADA = "pedido.*.entrega_confirmada"
ROUTING_RASTREADOR_ATUALIZADO = "pedido.*.rastreador_atualizado"
ROUTING_PEDIDO_PREPARADO = "pedido.*.preparado"


def routing_entrega_confirmada(id_pedido: UUID | str) -> str:
    """Routing key for EntregaConfirmada events."""
    return f"pedido.{id_pedido}.entrega_confirmada"


def routing_pedido_preparado(id_pedido: UUID | str) -> str:
    """Routing key for PedidoPreparado events."""
    return f"pedido.{id_pedido}.preparado"


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


def routing_rastreador_atualizado(id_pedido: UUID | str) -> str:
    """Routing key when ADM ressigns an order to another tracker."""
    return f"pedido.{id_pedido}.rastreador_atualizado"
