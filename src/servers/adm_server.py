"""Servidor Administrador (ADM).

Responsabilidades (docs/especificacao.md):
1. Acompanhar a disponibilidade dos servidores R (KeepAlive).
2. Solicitar ao SUP informações de rastreios com apenas um R associado após falha.
3. Enviar informações obtidas para um segundo (ou mais) servidor R.
4. Manter a lista de pedidos ainda não atribuídos a um entregador.
5. Participar da eleição de líder (Bully Algorithm) entre múltiplos ADMs.
"""

from src.core.models import AceitarPedido, ConfirmarEntrega, CriarPedido, KeepAlive


class ADMServer:
    """Coordena a criação de pedidos, o roteamento entre Servidores Rastreadores
    e a eleição de líder entre múltiplos Servidores Administradores."""

    def __init__(self, id_servidor: str):
        """Inicializa o estado do servidor ADM (id, mapa pedido -> servidor R, líder atual)."""
        raise NotImplementedError

    async def criar_pedido(self, requisicao: CriarPedido) -> None:
        """Processa CriarPedido e publica o evento PedidoDisponivel no broker."""
        raise NotImplementedError

    async def aceitar_pedido(self, requisicao: AceitarPedido) -> None:
        """Processa AceitarPedido, atribui o pedido a um Servidor Rastreador
        (via hash determinístico) e notifica cliente/entregador."""
        raise NotImplementedError

    async def confirmar_entrega(self, requisicao: ConfirmarEntrega) -> None:
        """Processa ConfirmarEntrega e publica o evento EntregaConfirmada."""
        raise NotImplementedError

    async def processar_keepalive(self, mensagem: KeepAlive) -> None:
        """Atualiza o estado de disponibilidade do servidor que enviou o heartbeat."""
        raise NotImplementedError

    async def detectar_falha_servidor_rastreador(self, id_servidor: str) -> None:
        """Reage à ausência de heartbeat de um Servidor Rastreador, solicitando
        a lista de backup ao SUP correspondente e redistribuindo os pedidos."""
        raise NotImplementedError

    async def iniciar_eleicao(self) -> None:
        """Inicia uma eleição de líder entre os Servidores Administradores (Bully Algorithm)."""
        raise NotImplementedError
