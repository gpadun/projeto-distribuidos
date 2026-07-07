"""Console simulator for a delivery driver."""

import argparse
import asyncio
import random
from time import time
from uuid import UUID

from src.core.models import LocalizacaoEntregador
from src.servers.tracker_server import TrackerServer


class MockDriver:
    """Generates periodic fake GPS updates for one driver/order pair."""

    def __init__(
        self,
        id_entregador: str,
        id_pedido: str,
        tracker_server: TrackerServer | None = None,
    ):
        self.id_entregador = id_entregador
        self.id_pedido = UUID(str(id_pedido))
        self.tracker_server = tracker_server
        self._latitude = -23.55052
        self._longitude = -46.633308

    async def gerar_localizacao_falsa(self) -> tuple[float, float]:
        """Move slightly around Sao Paulo to simulate a driver in transit."""
        self._latitude += random.uniform(-0.001, 0.001)
        self._longitude += random.uniform(-0.001, 0.001)
        return round(self._latitude, 6), round(self._longitude, 6)

    async def enviar_localizacoes_periodicamente(self, intervalo_segundos: float) -> None:
        """Send location events forever, or print them when no tracker is injected."""
        if self.tracker_server is not None:
            await self.tracker_server.registrar_entregador(self.id_entregador, self.id_pedido)

        while True:
            latitude, longitude = await self.gerar_localizacao_falsa()
            localizacao = LocalizacaoEntregador(
                idEntregador=self.id_entregador,
                idPedido=self.id_pedido,
                latitude=latitude,
                longitude=longitude,
                timestamp=int(time()),
            )
            if self.tracker_server is not None:
                await self.tracker_server.receber_localizacao(localizacao)
            else:
                print(localizacao)
            await asyncio.sleep(intervalo_segundos)


def main() -> None:
    """Run the driver simulator in print-only mode from the terminal."""
    parser = argparse.ArgumentParser(description="Simula um entregador enviando GPS falso.")
    parser.add_argument("--id-entregador", default="entregador-1")
    parser.add_argument("--id-pedido", required=True)
    parser.add_argument("--intervalo", type=float, default=2.0)
    args = parser.parse_args()

    driver = MockDriver(args.id_entregador, args.id_pedido)
    asyncio.run(driver.enviar_localizacoes_periodicamente(args.intervalo))


if __name__ == "__main__":
    main()
