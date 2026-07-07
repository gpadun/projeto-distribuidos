"""Tracker server (R) for delivery location updates."""

from typing import Any
from uuid import UUID

from src.core.models import EventoLocalizacao, LocalizacaoEntregador
from src.core.serialization import to_message_dict
from src.servers.support_server import SupportServer


class TrackerServer:
    """Receives driver locations, stores the newest one and publishes tracking events."""

    def __init__(
        self,
        id_servidor: str,
        publisher: Any | None = None,
        support_server: SupportServer | None = None,
    ):
        self.id_servidor = id_servidor
        self.publisher = publisher
        self.support_server = support_server
        self.entregadores_por_pedido: dict[UUID, str] = {}
        self.pedidos_por_entregador: dict[str, UUID] = {}
        self.ultimas_localizacoes: dict[UUID, LocalizacaoEntregador] = {}
        self.entregadores_desconectados: set[str] = set()

    async def registrar_entregador(self, id_entregador: str, id_pedido: str | UUID) -> None:
        """Associate a driver with a delivery order handled by this tracker."""
        pedido_uuid = id_pedido if isinstance(id_pedido, UUID) else UUID(str(id_pedido))
        self.entregadores_por_pedido[pedido_uuid] = id_entregador
        self.pedidos_por_entregador[id_entregador] = pedido_uuid
        self.entregadores_desconectados.discard(id_entregador)
        await self._sincronizar_suporte()

    async def receber_localizacao(self, localizacao: LocalizacaoEntregador) -> None:
        """Store and publish a location if it is newer than the current one."""
        entregador_esperado = self.entregadores_por_pedido.get(localizacao.idPedido)
        if entregador_esperado is None:
            raise ValueError("pedido nao registrado neste servidor")
        if entregador_esperado != localizacao.idEntregador:
            raise ValueError("entregador nao esta associado a este pedido")

        anterior = self.ultimas_localizacoes.get(localizacao.idPedido)
        if anterior and anterior.timestamp >= localizacao.timestamp:
            return

        self.ultimas_localizacoes[localizacao.idPedido] = localizacao
        evento = EventoLocalizacao(
            idPedido=localizacao.idPedido,
            latitude=localizacao.latitude,
            longitude=localizacao.longitude,
            timestamp=localizacao.timestamp,
        )
        await self.publicar_localizacao(evento)
        await self._sincronizar_suporte()

    async def publicar_localizacao(self, evento: EventoLocalizacao) -> None:
        """Publish a location event to the tracking topic for the order."""
        if self.publisher is None:
            return
        self.publisher.publish(
            exchange="rastreio",
            routing_key=f"pedido.{evento.idPedido}",
            message=to_message_dict(evento),
        )

    async def notificar_desconexao(self, id_entregador: str) -> None:
        """Publish and store a driver disconnection notification."""
        self.entregadores_desconectados.add(id_entregador)
        id_pedido = self.pedidos_por_entregador.get(id_entregador)
        if self.publisher and id_pedido:
            self.publisher.publish(
                exchange="rastreio",
                routing_key=f"pedido.{id_pedido}.desconexao",
                message={"idPedido": str(id_pedido), "idEntregador": id_entregador},
            )
        await self._sincronizar_suporte()

    def snapshot_rastreios(self) -> dict[str, dict[str, Any]]:
        """Return a JSON-friendly snapshot for ADM/SUP recovery."""
        snapshot: dict[str, dict[str, Any]] = {}
        for id_pedido, id_entregador in self.entregadores_por_pedido.items():
            localizacao = self.ultimas_localizacoes.get(id_pedido)
            snapshot[str(id_pedido)] = {
                "idEntregador": id_entregador,
                "idServidorRastreador": self.id_servidor,
                "ultimaLocalizacao": to_message_dict(localizacao) if localizacao else None,
            }
        return snapshot

    async def _sincronizar_suporte(self) -> None:
        if self.support_server is not None:
            await self.support_server.sincronizar_rastreios(self.snapshot_rastreios())
