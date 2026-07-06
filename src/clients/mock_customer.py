"""Simulador de cliente (mock_customer).

Cria pedidos via requisição síncrona ao Servidor ADM e assina o rastreio de
localização do pedido correspondente via broker (Publish-Subscribe).
"""


class MockCustomer:
    """Simula um cliente criando um pedido e acompanhando o rastreio da entrega."""

    def __init__(self, id_cliente: str, id_restaurante: str):
        """Associa o mock a um cliente e ao restaurante alvo do pedido."""
        raise NotImplementedError

    async def criar_pedido(self) -> str:
        """Envia CriarPedido ao Servidor ADM e retorna o idPedido gerado."""
        raise NotImplementedError

    async def assinar_rastreio(self, id_pedido: str) -> None:
        """Envia SubscribeRastreio e passa a receber EventoLocalizacao via broker."""
        raise NotImplementedError

    async def confirmar_entrega(self, id_pedido: str) -> None:
        """Envia ConfirmarEntrega ao Servidor ADM."""
        raise NotImplementedError


def main() -> None:
    """Ponto de entrada para executar o simulador de cliente via terminal."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
