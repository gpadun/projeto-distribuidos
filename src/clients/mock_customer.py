"""Console simulator for a customer."""

import argparse
from time import time
from uuid import uuid4, UUID
import os

from src.core.models import ConfirmarEntrega, CriarPedido
from src.servers.adm_server import ADMServer
from src.clients.customer_broker import CustomerBrokerError, confirmar_entrega_via_adm, executar_cliente_broker


def _parse_id_pedido(raw: str | None) -> UUID | None:
    """Parse order UUID from CLI input with a clear error message."""
    if raw is None:
        return None
    try:
        return UUID(str(raw).strip())
    except ValueError as exc:
        raise CustomerBrokerError(
            f"id-pedido invalido: {raw!r}. Use um UUID real, por exemplo "
            "00000000-0000-0000-0000-000000000001"
        ) from exc


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
    parser = argparse.ArgumentParser(description="Simula um cliente.")
    parser.add_argument(
        "--acao",
        choices=["criar", "rastrear", "demo", "confirmar"],
        default="demo",
        help="criar: POST /pedidos; rastrear: assina broker; demo: criar+rastrear; confirmar: POST /confirmar",
    )
    parser.add_argument("--id-cliente", default="cliente-1")
    parser.add_argument("--id-restaurante", default="restaurante-1")
    parser.add_argument("--id-pedido", default=None, help="UUID do pedido")
    parser.add_argument(
        "--adm-url",
        default=None,
        help="URL do ADM lider (padrao: ADM_URL ou http://127.0.0.1:8003)",
    )
    args = parser.parse_args()

    adm_url = args.adm_url or os.getenv("ADM_URL", "http://127.0.0.1:8003")

    if args.acao == "confirmar":
        if not args.id_pedido:
            parser.error("--id-pedido e obrigatorio no modo confirmar")
        id_pedido = _parse_id_pedido(args.id_pedido)
        confirmar_entrega_via_adm(adm_url, args.id_cliente, id_pedido)
        print(f"[cliente] entrega confirmada: {id_pedido}")
        return

    id_pedido = _parse_id_pedido(args.id_pedido)

    executar_cliente_broker(
        id_cliente=args.id_cliente,
        id_restaurante=args.id_restaurante,
        adm_url=adm_url,
        id_pedido=id_pedido,
        acao=args.acao,
    )


if __name__ == "__main__":
    main()
