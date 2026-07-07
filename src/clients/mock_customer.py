"""Console simulator for a customer."""

import argparse
import asyncio
from time import time
from uuid import uuid4

from src.core.models import ConfirmarEntrega, CriarPedido
from src.servers.adm_server import ADMServer


class MockCustomer:
    """Creates an order and can subscribe/confirm delivery in demonstrations."""

    def __init__(
        self,
        id_cliente: str,
        id_restaurante: str,
        adm_server: ADMServer | None = None,
    ):
        self.id_cliente = id_cliente
        self.id_restaurante = id_restaurante
        self.adm_server = adm_server

    async def criar_pedido(self) -> str:
        """Create an order through ADM when injected, otherwise just generate the payload."""
        requisicao = CriarPedido(
            idPedido=uuid4(),
            idCliente=self.id_cliente,
            idRestaurante=self.id_restaurante,
            timestamp=int(time()),
        )
        if self.adm_server is not None:
            await self.adm_server.criar_pedido(requisicao)
        print(f"Pedido criado: {requisicao.idPedido}")
        return str(requisicao.idPedido)

    async def assinar_rastreio(self, id_pedido: str) -> None:
        """Print the tracking topic the customer should subscribe to."""
        print(f"Cliente {self.id_cliente} assinando topico pedido.{id_pedido}")

    async def confirmar_entrega(self, id_pedido: str) -> None:
        """Confirm delivery through ADM when available."""
        requisicao = ConfirmarEntrega(
            idPedido=id_pedido,
            idCliente=self.id_cliente,
            timestamp=int(time()),
        )
        if self.adm_server is not None:
            await self.adm_server.confirmar_entrega(requisicao)
        print(f"Entrega confirmada: {id_pedido}")


def main() -> None:
    """Run the customer simulator from the terminal."""
    parser = argparse.ArgumentParser(description="Simula um cliente criando pedido.")
    parser.add_argument("--id-cliente", default="cliente-1")
    parser.add_argument("--id-restaurante", default="restaurante-1")
    args = parser.parse_args()

    customer = MockCustomer(args.id_cliente, args.id_restaurante)
    asyncio.run(customer.criar_pedido())


if __name__ == "__main__":
    main()
