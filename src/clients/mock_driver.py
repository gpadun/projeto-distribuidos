"""Console simulator for a delivery driver."""

import argparse
import asyncio
from time import time
from uuid import UUID

from src.core.models import LocalizacaoEntregador
from src.servers.tracker_server import TrackerServer
from src.clients.driver_broker import executar_entregador_broker


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
        self._origem = (-23.55052, -46.633308)
        self._destino = (-23.55612, -46.63955)
        self._passo = 0
        self._total_passos = 12

    async def gerar_localizacao_falsa(self) -> tuple[float, float]:
        """Move from a fixed origin to a fixed destination in Sao Paulo."""
        progresso = min(self._passo / self._total_passos, 1.0)
        latitude = self._origem[0] + ((self._destino[0] - self._origem[0]) * progresso)
        longitude = self._origem[1] + ((self._destino[1] - self._origem[1]) * progresso)
        self._passo += 1
        return round(latitude, 6), round(longitude, 6)

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
    """Run the driver simulator from the terminal."""
    parser = argparse.ArgumentParser(description="Simula um entregador.")
    parser.add_argument(
        "--modo",
        choices=["broker", "gps"],
        default="broker",
        help="broker: ouve PedidoDisponivel; gps: envia localizacoes falsas",
    )
    parser.add_argument("--id-entregador", default="entregador-1")
    parser.add_argument("--id-pedido", help="obrigatorio no modo gps")
    parser.add_argument("--intervalo", type=float, default=2.0)
    parser.add_argument(
        "--adm-url",
        default=None,
        help="URL do ADM lider (padrao: ADM_URL ou http://127.0.0.1:8003)",
    )
    parser.add_argument(
        "--sem-aceitar-automatico",
        action="store_true",
        help="no modo broker, apenas imprime PedidoDisponivel",
    )
    args = parser.parse_args()

    if args.modo == "broker":
        executar_entregador_broker(
            id_entregador=args.id_entregador,
            adm_url=args.adm_url,
            aceitar_automatico=not args.sem_aceitar_automatico,
        )
        return

    if not args.id_pedido:
        parser.error("--id-pedido e obrigatorio no modo gps")

    driver = MockDriver(args.id_entregador, args.id_pedido)
    asyncio.run(driver.enviar_localizacoes_periodicamente(args.intervalo))


if __name__ == "__main__":
    main()
