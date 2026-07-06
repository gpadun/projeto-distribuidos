"""Servidor Rastreador (R).

Responsabilidades (docs/especificacao.md):
1. Manter lista de entregadores conectados e sua localização mais recente.
2. Enviar a localização mais recente do entregador associado ao cliente quando solicitado.
3. Notificar cliente e restaurante sobre a desconexão do entregador.
"""

from src.core.models import EventoLocalizacao, LocalizacaoEntregador


class TrackerServer:
    """Recebe localizações de entregadores atribuídos a este servidor e publica
    eventos de rastreio para os clientes assinantes via broker."""

    def __init__(self, id_servidor: str):
        """Inicializa o estado do servidor R (id, entregadores/pedidos associados)."""
        raise NotImplementedError

    async def registrar_entregador(self, id_entregador: str, id_pedido: str) -> None:
        """Associa um entregador a um pedido sob responsabilidade deste servidor."""
        raise NotImplementedError

    async def receber_localizacao(self, localizacao: LocalizacaoEntregador) -> None:
        """Recebe a localização enviada pelo entregador e publica EventoLocalizacao."""
        raise NotImplementedError

    async def publicar_localizacao(self, evento: EventoLocalizacao) -> None:
        """Publica o evento de localização no broker para os clientes assinantes."""
        raise NotImplementedError

    async def notificar_desconexao(self, id_entregador: str) -> None:
        """Notifica cliente e restaurante sobre a desconexão do entregador."""
        raise NotImplementedError
