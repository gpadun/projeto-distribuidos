"""Administrator server (ADM)."""

import re
from time import time
from typing import Any
from uuid import UUID
from collections.abc import Awaitable, Callable

from src.core.models import (
    AceitarPedido,
    AtualizacaoRoteamento,
    ConfirmarEntrega,
    CriarPedido,
    EntregaConfirmada,
    KeepAlive,
    Pedido,
    PedidoDisponivel,
    StatusPedido,
    TipoServidor,
)
from src.core.routing import escolher_servidor_consistent_hash
from src.core.serialization import to_message_dict
from src.servers.support_server import SupportServer


class ADMServer:
    """Coordinates orders, tracker routing, heartbeat state and leader election."""

    def __init__(
        self,
        id_servidor: str,
        servidores_rastreadores: list[str] | None = None,
        publisher: Any | None = None,
        servidores_adm: list[str] | None = None,
        support_servers: dict[str, SupportServer] | None = None,
        heartbeat_timeout: float = 10.0,
        keepalive_sender: Callable[[str, KeepAlive], Awaitable[None]] | None = None,
    ):
        self.id_servidor = id_servidor
        self.publisher = publisher
        self.servidores_rastreadores = list(servidores_rastreadores or [])
        self.servidores_rastreadores_ativos = set(self.servidores_rastreadores)
        self.support_servers = support_servers or {}
        self.heartbeat_timeout = heartbeat_timeout
        self.keepalive_sender = keepalive_sender
        instante_inicial = time()

        self.pedidos: dict[UUID, Pedido] = {}
        self.pedidos_sem_entregador: dict[UUID, Pedido] = {}
        self.mapa_pedido_servidor: dict[UUID, str] = {}
        self.ultimo_keepalive: dict[str, float] = {
            id_servidor: instante_inicial for id_servidor in self.servidores_rastreadores
        }

        self.servidores_adm = sorted(set(servidores_adm or [id_servidor]))
        self.lider_atual = self._maior_id(self.servidores_adm)

        self.servdores_adm_ativos: set[str]
        self.servidores_adm_ativos = set(self.servidores_adm)
        for id_adm in self.servidores_adm:
            self.ultimo_keepalive[id_adm] = instante_inicial

    async def criar_pedido(self, requisicao: CriarPedido) -> Pedido:
        """Create an order and publish PedidoDisponivel for subscribed drivers."""
        pedido = Pedido(
            idPedido=requisicao.idPedido,
            idCliente=requisicao.idCliente,
            idRestaurante=requisicao.idRestaurante,
            timestamp=requisicao.timestamp,
        )
        self.pedidos[pedido.idPedido] = pedido
        self.pedidos_sem_entregador[pedido.idPedido] = pedido

        evento = PedidoDisponivel(
            idPedido=pedido.idPedido,
            idRestaurante=pedido.idRestaurante,
            timestamp=pedido.timestamp,
        )
        self._publish("pedidos", "pedido.disponivel", evento)
        return pedido

    async def aceitar_pedido(self, requisicao: AceitarPedido) -> Pedido:
        """Assign an order to a driver and choose the responsible tracker by hash."""
        pedido = self.pedidos.get(requisicao.idPedido)
        if pedido is None:
            raise KeyError("pedido nao encontrado")

        servidor = self._escolher_servidor_rastreador(requisicao.idPedido)
        pedido.idEntregador = requisicao.idEntregador
        pedido.servidorRastreadorResponsavel = servidor
        pedido.status = StatusPedido.COM_SERVIDOR_RASTREADOR
        self.pedidos_sem_entregador.pop(requisicao.idPedido, None)
        self.mapa_pedido_servidor[requisicao.idPedido] = servidor

        atualizacao = AtualizacaoRoteamento(
            idPedido=requisicao.idPedido,
            idServidorRastreador=servidor,
            timestamp=requisicao.timestamp,
        )
        self._publish("infra", f"roteamento.{servidor}", atualizacao)
        return pedido

    async def confirmar_entrega(self, requisicao: ConfirmarEntrega) -> EntregaConfirmada:
        """Confirm delivery and notify the driver through the broker."""
        pedido = self.pedidos.get(requisicao.idPedido)
        if pedido is None:
            raise KeyError("pedido nao encontrado")
        if pedido.idCliente != requisicao.idCliente:
            raise ValueError("cliente nao corresponde ao pedido")

        evento = EntregaConfirmada(idPedido=requisicao.idPedido, timestamp=requisicao.timestamp)
        self._publish("pedidos", f"pedido.{requisicao.idPedido}.entrega_confirmada", evento)
        self.pedidos.pop(requisicao.idPedido, None)
        self.pedidos_sem_entregador.pop(requisicao.idPedido, None)
        self.mapa_pedido_servidor.pop(requisicao.idPedido, None)
        return evento

    async def processar_keepalive(self, mensagem: KeepAlive) -> None:
        """Record the latest heartbeat received from a server."""
        self.ultimo_keepalive[mensagem.idServidor] = time()
        if (
            mensagem.tipoServidor == TipoServidor.RASTREADOR
            and mensagem.idServidor in self.servidores_rastreadores
        ):
            self.servidores_rastreadores_ativos.add(mensagem.idServidor)

        elif (
            mensagem.tipoServidor == TipoServidor.ADM 
            and mensagem.idServidor in self.servidores_adm
        ):
            self.servidores_adm_ativos.add(mensagem.idServidor)

    def criar_keepalive_proprio(self) -> KeepAlive:
        return KeepAlive(
            idServidor=self.id_servidor,
            tipoServidor=TipoServidor.ADM,
            timestamp=int(time()),
        )
    
    def registrar_keepalive_local(self) -> None:
        self.ultimo_keepalive[self.id_servidor] = time()
        self.servidores_adm_ativos.add(self.id_servidor)

    def adms_com_heartbeat_expirado(self, agora: float | None = None) -> list[str]:
        instance = time() if agora is None else agora
        expirados = []

        for id_adm in sorted(self.servidores_adm_ativos):
            if id_adm == self.id_servidor:
                continue # nunca considerar a si mesmo expirado aqui

            ultimo = self.ultimo_keepalive.get(id_adm)
            if ultimo is not None and instance - ultimo > self.heartbeat_timeout:
                expirados.append(id_adm)

        return expirados
    
    def processar_expiracao_adms(self, agora: float | None = None) -> list[str]:
        expirados = self.adms_com_heartbeat_expirado(agora)
        for id_adm in expirados:
            self.servidores_adm_ativos.discard(id_adm)
        return expirados
    
    async def executar_ciclo_keepalive(self) -> None:
        self.registrar_keepalive_local()

        if self.keepalive_sender is None:
            return
        
        mensagem = self.criar_keepalive_proprio()

        for id_adm in self.servidores_adm:
            if id_adm == self.id_servidor:
                continue
            await self.keepalive_sender(id_adm, mensagem)
    
    async def detectar_falha_servidor_rastreador(self, id_servidor: str) -> dict[UUID, str]:
        """Remove a failed tracker and redistribute its orders to active trackers."""
        self.servidores_rastreadores_ativos.discard(id_servidor)
        afetados = [
            id_pedido
            for id_pedido, servidor in self.mapa_pedido_servidor.items()
            if servidor == id_servidor
        ]

        support = self.support_servers.get(id_servidor)
        if support is not None:
            backup = await support.enviar_lista_backup()
            afetados_set = set(afetados)
            for id_pedido_str in backup:
                try:
                    pedido_uuid = UUID(id_pedido_str)
                except (TypeError, ValueError):
                    continue
                if pedido_uuid not in afetados_set:
                    afetados.append(pedido_uuid)
                    afetados_set.add(pedido_uuid)

        redistribuidos: dict[UUID, str] = {}
        for id_pedido in afetados:
            novo_servidor = self._escolher_servidor_rastreador(id_pedido)
            self.mapa_pedido_servidor[id_pedido] = novo_servidor
            pedido = self.pedidos.get(id_pedido)
            if pedido:
                pedido.servidorRastreadorResponsavel = novo_servidor
            redistribuidos[id_pedido] = novo_servidor
            self._publish(
                "infra",
                f"roteamento.{novo_servidor}",
                AtualizacaoRoteamento(
                    idPedido=id_pedido,
                    idServidorRastreador=novo_servidor,
                    timestamp=int(time()),
                ),
            )
        return redistribuidos

    async def iniciar_eleicao(self) -> str:
        """Run a deterministic Bully election: the highest ADM id becomes leader."""
        self.lider_atual = self._maior_id(self.servidores_adm)
        return self.lider_atual

    def servidores_com_heartbeat_expirado(self, agora: float | None = None) -> list[str]:
        """Return tracker ids whose heartbeat is older than the configured timeout."""
        instante = time() if agora is None else agora
        expirados = []
        for id_servidor in sorted(self.servidores_rastreadores_ativos):
            ultimo = self.ultimo_keepalive.get(id_servidor)
            if ultimo is not None and instante - ultimo > self.heartbeat_timeout:
                expirados.append(id_servidor)
        return expirados

    def _escolher_servidor_rastreador(self, id_pedido: UUID) -> str:
        ativos = sorted(self.servidores_rastreadores_ativos)
        if not ativos:
            raise RuntimeError("nenhum servidor rastreador ativo")
        return escolher_servidor_consistent_hash(id_pedido, ativos)

    def _publish(self, exchange: str, routing_key: str, model) -> None:
        if self.publisher is not None:
            self.publisher.publish(exchange, routing_key, to_message_dict(model))

    @staticmethod
    def _maior_id(ids: list[str]) -> str:
        def chave(id_servidor: str) -> tuple[int, str]:
            match = re.search(r"(\d+)$", id_servidor)
            if match:
                return (int(match.group(1)), id_servidor)
            return (0, id_servidor)

        return max(ids, key=chave)
