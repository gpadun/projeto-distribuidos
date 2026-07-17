"""Administrator server (ADM)."""

import re

import httpx
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
    IniciarEleicao,
    RespostaEleicao,
    NovoLider,
)
from src.core.routing import escolher_servidor_consistent_hash
from src.core.serialization import to_message_dict
from src.servers.support_server import SupportServer

from src.broker.topology import (
    EXCHANGE_INFRA,
    EXCHANGE_PEDIDOS,
    ROUTING_PEDIDO_DISPONIVEL,
    routing_entrega_confirmada,
    routing_rastreador_atualizado,
    routing_roteamento,
)


class NaoELiderError(Exception):
    """Raised when a non-leader ADM tries to process a leader-only command."""

    def __init__(self, id_servidor: str, lider_atual: str):
        self.id_servidor = id_servidor
        self.lider_atual = lider_atual
        super().__init__(
            f"servidor {id_servidor} nao e o lider ADM; lider atual: {lider_atual}"
        )


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
        on_lider_caiu: Callable[[str], Awaitable[None]] | None = None,
        election_sender: Callable[[str, IniciarEleicao | RespostaEleicao | NovoLider], Awaitable[None]] | None = None,
        eleicao_timeout: float = 2.0,
        support_urls: dict[str, str] | None = None,
    ):
        self.id_servidor = id_servidor
        self.publisher = publisher
        self.servidores_rastreadores = list(servidores_rastreadores or [])
        self.servidores_rastreadores_ativos: set[str] = set()
        self.support_servers = support_servers or {}
        self.heartbeat_timeout = heartbeat_timeout
        self.keepalive_sender = keepalive_sender
        self.on_lider_caiu = on_lider_caiu
        self.election_sender = election_sender
        self.eleicao_timeout = eleicao_timeout
        instante_inicial = time()

        self.pedidos: dict[UUID, Pedido] = {}
        self.pedidos_sem_entregador: dict[UUID, Pedido] = {}
        self.mapa_pedido_servidor: dict[UUID, str] = {}
        self.ultimo_keepalive: dict[str, float] = {}

        self.servidores_adm = sorted(set(servidores_adm or [id_servidor]))
        self.lider_atual = self._maior_id(self.servidores_adm)

        self.servidores_adm_ativos = set(self.servidores_adm)
        for id_adm in self.servidores_adm:
            self.ultimo_keepalive[id_adm] = instante_inicial

        self.lider_disponivel: bool = True
        self.aguardando_eleicao: bool = False
        self.id_lider_anterior: str | None = None
        self.eleicao_em_andamento: bool = False
        self.recebeu_resposta_de_maior: bool = False

        self.support_urls = support_urls or {}
    

    async def criar_pedido(self, requisicao: CriarPedido) -> Pedido:
        """Create an order and publish PedidoDisponivel for subscribed drivers."""
        self.garantir_lider()
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
        self._publish(EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL, evento)
        return pedido

    async def aceitar_pedido(self, requisicao: AceitarPedido) -> Pedido:
        """Assign an order to a driver and choose the responsible tracker by hash."""
        self.garantir_lider()
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
            idEntregador=requisicao.idEntregador,
            timestamp=requisicao.timestamp,
        )
        self._publish(EXCHANGE_INFRA, routing_roteamento(servidor), atualizacao)
        return pedido

    async def confirmar_entrega(self, requisicao: ConfirmarEntrega) -> EntregaConfirmada:
        """Confirm delivery and notify the driver through the broker."""
        self.garantir_lider()
        pedido = self.pedidos.get(requisicao.idPedido)
        if pedido is None:
            raise KeyError("pedido nao encontrado")
        if pedido.idCliente != requisicao.idCliente:
            raise ValueError("cliente nao corresponde ao pedido")

        evento = EntregaConfirmada(idPedido=requisicao.idPedido, timestamp=requisicao.timestamp)
        self._publish(
            EXCHANGE_PEDIDOS,
            routing_entrega_confirmada(requisicao.idPedido),
            evento,
        )
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
        if id_servidor not in self.servidores_rastreadores_ativos:
            return {}

        backup = await self._buscar_backup_sup(id_servidor)
        self.servidores_rastreadores_ativos.discard(id_servidor)

        afetados = [
            id_pedido
            for id_pedido, servidor in self.mapa_pedido_servidor.items()
            if servidor == id_servidor
        ]
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
            if not self.servidores_rastreadores_ativos:
                break

            novo_servidor = self._escolher_servidor_rastreador(id_pedido)
            pedido = self.pedidos.get(id_pedido)
            id_entregador = pedido.idEntregador if pedido else None
            if not id_entregador:
                dados = backup.get(str(id_pedido), {})
                id_entregador = dados.get("idEntregador")

            self.mapa_pedido_servidor[id_pedido] = novo_servidor
            if pedido:
                pedido.servidorRastreadorResponsavel = novo_servidor
            redistribuidos[id_pedido] = novo_servidor

            self._publish(
                EXCHANGE_INFRA,
                routing_roteamento(novo_servidor),
                AtualizacaoRoteamento(
                    idPedido=id_pedido,
                    idServidorRastreador=novo_servidor,
                    idEntregador=id_entregador,
                    timestamp=int(time()),
                ),
            )

            if id_entregador:
                self._publish(
                    EXCHANGE_PEDIDOS,
                    routing_rastreador_atualizado(id_pedido),
                    {
                        "idPedido": str(id_pedido),
                        "idServidorRastreador": novo_servidor,
                        "idEntregador": id_entregador,
                        "timestamp": int(time()),
                    },
                )

            print(
                f"[adm] pedido {id_pedido} redistribuido "
                f"{id_servidor} -> {novo_servidor}"
            )

        return redistribuidos

    async def iniciar_eleicao(self) -> str:
        """Run a deterministic Bully election: the highest ADM id becomes leader."""
        if self.eleicao_em_andamento:
            return self.lider_atual
        
        self.eleicao_em_andamento = True
        self.recebeu_resposta_de_maior = False

        maiores = self._adms_ativos_com_id_maior_que(self.id_servidor)

        # Sou o maior ID ativo -> viro líder
        if not maiores:
            return await self._tornar_lider()
        
        # Mando eleicao para todos os maiores
        for id_adm in maiores:
            await self._enviar_iniciar_eleicao(id_adm)

        # Espero respostas dentro do timeout
        await self._aguardar_timeout_eleicao()

        # Alguém maior respondeu -> desisto
        if self.recebeu_resposta_de_maior:
            self.eleicao_em_andamento = False
            return self.lider_atual # NovoLider vai atualizar depois
        
        # Ninguém respondeu -> eu sou o líder
        return await self._tornar_lider()

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
            message = model if isinstance(model, dict) else to_message_dict(model)
            self.publisher.publish(exchange, routing_key, message)

    @staticmethod
    def _maior_id(ids: list[str]) -> str:
        def chave(id_servidor: str) -> tuple[int, str]:
            match = re.search(r"(\d+)$", id_servidor)
            if match:
                return (int(match.group(1)), id_servidor)
            return (0, id_servidor)

        return max(ids, key=chave)
    
    @staticmethod
    def _chave_id(id_servidor: str) -> tuple[int, str]:
        match = re.search(r"(\d+)$", id_servidor)
        if match:
            return (int(match.group(1)), id_servidor)
        return (0, id_servidor)

    @staticmethod
    def _maior_id(ids: list[str]) -> str:
        return max(ids, key=ADMServer._chave_id)

    def _id_e_maior_que(self, id_a: str, id_b: str) -> bool:
        return self._chave_id(id_a) > self._chave_id(id_b)

    def _adms_ativos_com_id_maior_que(self, id_servidor: str) -> list[str]:
        return sorted(
            id_adm
            for id_adm in self.servidores_adm_ativos
            if id_adm != id_servidor and self._id_e_maior_que(id_adm, id_servidor)
        )

    def _adms_ativos_com_id_menor_que(self, id_servidor: str) -> list[str]:
        return sorted(
            id_adm
            for id_adm in self.servidores_adm_ativos
            if id_adm != id_servidor and self._id_e_maior_que(id_servidor, id_adm)
        )


    def sou_lider(self) -> bool:
        return self.lider_atual == self.id_servidor

    def garantir_lider(self) -> None:
        """Raise NaoELiderError when this ADM is not the current cluster leader."""
        if not self.sou_lider():
            raise NaoELiderError(self.id_servidor, self.lider_atual)

    def lider_com_heartbeat_expirado(self, agora: float | None = None) -> bool:
        if self.sou_lider():
            return False
        
        instance = time() if agora is None else agora
        ultimo = self.ultimo_keepalive.get(self.lider_atual)

        if ultimo is None:
            return True
        
        return instance - ultimo > self.heartbeat_timeout

    async def detectar_falha_lider(self, agora: float | None = None) -> bool:
        if self.sou_lider():
            return False
        
        if not self.lider_disponivel:
            return True # falha já detectado, ainda sem eleição
        
        expirou = self.lider_com_heartbeat_expirado(agora)
        lider_inativo = self.lider_atual not in self.servidores_adm_ativos

        if not expirou and not lider_inativo:
            return False
        
        self.id_lider_anterior = self.lider_atual
        self.lider_disponivel = False
        self.aguardando_eleicao = True
        self.servidores_adm_ativos.discard(self.lider_atual)

        if self.on_lider_caiu is not None:
            await self.on_lider_caiu(self.id_lider_anterior)

        return True
    
    async def executar_ciclo_monitoramento(self) -> bool:
        await self.executar_ciclo_keepalive()
        self.processar_expiracao_adms()
        falha_lider = await self.detectar_falha_lider()
        
        if self.sou_lider():
            for id_rastreador in self.servidores_com_heartbeat_expirado():
                print(
                    f"[adm {self.id_servidor}] rastreador {id_rastreador} "
                    "com heartbeat expirado"
                )
                redistribuidos = await self.detectar_falha_servidor_rastreador(
                    id_rastreador
                )
                if redistribuidos:
                    print(
                        f"[adm {self.id_servidor}] pedidos redistribuidos: "
                        f"{ {str(k): v for k, v in redistribuidos.items()} }"
                    )

        return falha_lider
    
    async def _enviar_iniciar_eleicao(self, id_destino: str) -> None:
        if self.election_sender is None:
            return
        mensagem = IniciarEleicao(
            idServidorOrigem=self.id_servidor,
            idServidorDestino=id_destino,
            idLiderAnterior=self.id_lider_anterior,
            timestamp=int(time()),
        )
        await self.election_sender(id_destino, mensagem)

    async def _enviar_resposta_eleicao(self, id_destino: str) -> None:
        if self.election_sender is None:
            return

        mensagem = RespostaEleicao(
            idServidorOrigem=self.id_servidor,
            idServidorDestino=id_destino,
            timestamp=int(time()),
        )
        await self.election_sender(id_destino, mensagem)

    async def _enviar_novo_lider(self, id_destino: str, mensagem: NovoLider) -> None:
        if self.election_sender is None:
            return

        await self.election_sender(id_destino, mensagem)

    async def _aguardar_timeout_eleicao(self) -> None:
        import asyncio

        inicio = time()
        while time() - inicio < self.eleicao_timeout:
            if self.recebeu_resposta_de_maior:
                return
            await asyncio.sleep(0.05)

    async def _tornar_lider(self) -> str:
        self.lider_atual = self.id_servidor
        self.lider_disponivel = True
        self.aguardando_eleicao = False
        self.eleicao_em_andamento = False

        mensagem = NovoLider(
            idServidor=self.id_servidor,
            idLiderAnterior=self.id_lider_anterior,
            timestamp=int(time()),
        )

        for id_adm in self._adms_ativos_com_id_menor_que(self.id_servidor):
            await self._enviar_novo_lider(id_adm, mensagem)

        return self.lider_atual
    
    async def processar_iniciar_eleicao(self, mensagem: IniciarEleicao) -> None:
        # 1. Responde para quem pediu
        await self._enviar_resposta_eleicao(mensagem.idServidorOrigem)

        # 2. Dispura entre os maiores que eu
        await self.iniciar_eleicao()

    async def processar_resposta_eleicao(self, mensagem: RespostaEleicao) -> None:
        if mensagem.idServidorDestino != self.id_servidor:
            return

        if self._id_e_maior_que(mensagem.idServidorOrigem, self.id_servidor):
            self.recebeu_resposta_de_maior = True

    async def processar_novo_lider(self, mensagem: NovoLider) -> None:
        self.lider_atual = mensagem.idServidor
        self.lider_disponivel = True
        self.aguardando_eleicao = False
        self.eleicao_em_andamento = False

    async def _buscar_backup_sup(self, id_rastreador: str) -> dict:
        support = self.support_servers.get(id_rastreador)
        if support is not None:
            return await support.enviar_lista_backup()
        
        url = self.support_urls.get(id_rastreador)
        if not url:
            return {}

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url.rstrip('/')}/backup")
            response.raise_for_status()
            return response.json()
