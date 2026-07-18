"""Tests for order-to-tracker map replication between ADM peers."""

import asyncio
from uuid import uuid4

from src.core.models import (
    AceitarPedido,
    ConfirmarEntrega,
    CriarPedido,
    KeepAlive,
    ReplicacaoRoteamento,
    TipoServidor,
)
from src.servers.adm_server import ADMServer


class ClusterRouter:
    def __init__(self):
        self.adms: dict[str, ADMServer] = {}
        self.mortos: set[str] = set()

    def registrar(self, adm: ADMServer) -> None:
        self.adms[adm.id_servidor] = adm

    def marcar_morto(self, id_adm: str) -> None:
        self.mortos.add(id_adm)
        self.adms.pop(id_adm, None)

    async def enviar_replicacao(self, id_destino: str, mensagem: ReplicacaoRoteamento) -> None:
        if id_destino in self.mortos:
            return
        await self.adms[id_destino].processar_replicacao_roteamento(mensagem)

    async def consultar_estado(self, id_destino: str) -> dict:
        adm = self.adms[id_destino]
        return {
            "roteamento": {str(k): v for k, v in adm.mapa_pedido_servidor.items()},
            "pedidosDetalhe": adm.snapshot_pedidos(),
            "pedidosSemEntregador": adm.snapshot_pedidos_sem_entregador(),
        }


def criar_cluster(ids: list[str], router: ClusterRouter) -> dict[str, ADMServer]:
    adms = {}
    for id_adm in ids:
        adm = ADMServer(
            id_servidor=id_adm,
            servidores_adm=ids,
            servidores_rastreadores=["rastreador-1", "rastreador-2"],
            replication_sender=router.enviar_replicacao,
            state_fetcher=router.consultar_estado,
            eleicao_timeout=0.2,
        )
        router.registrar(adm)
        adms[id_adm] = adm
    return adms


def run(coro):
    return asyncio.run(coro)


def _ativar_rastreadores(adm: ADMServer) -> None:
    for id_rastreador in ("rastreador-1", "rastreador-2"):
        run(
            adm.processar_keepalive(
                KeepAlive(
                    idServidor=id_rastreador,
                    tipoServidor=TipoServidor.RASTREADOR,
                    timestamp=1,
                )
            )
        )


def test_lider_propaga_roteamento_ao_aceitar_pedido():
    router = ClusterRouter()
    adms = criar_cluster(["adm-1", "adm-2", "adm-3"], router)
    lider = adms["adm-3"]
    lider.lider_atual = "adm-3"
    id_pedido = uuid4()

    run(
        lider.criar_pedido(
            CriarPedido(
                idPedido=id_pedido,
                idCliente="cliente-1",
                idRestaurante="restaurante-1",
                timestamp=1,
            )
        )
    )
    _ativar_rastreadores(lider)

    pedido = run(
        lider.aceitar_pedido(
            AceitarPedido(
                idPedido=id_pedido,
                idEntregador="entregador-1",
                timestamp=2,
            )
        )
    )

    assert adms["adm-1"].mapa_pedido_servidor[id_pedido] == pedido.servidorRastreadorResponsavel
    assert adms["adm-2"].mapa_pedido_servidor[id_pedido] == pedido.servidorRastreadorResponsavel


def test_lider_propaga_remocao_ao_confirmar_entrega():
    router = ClusterRouter()
    adms = criar_cluster(["adm-1", "adm-2"], router)
    lider = adms["adm-2"]
    lider.lider_atual = "adm-2"
    id_pedido = uuid4()

    run(
        lider.criar_pedido(
            CriarPedido(
                idPedido=id_pedido,
                idCliente="cliente-1",
                idRestaurante="restaurante-1",
                timestamp=1,
            )
        )
    )
    _ativar_rastreadores(lider)
    run(
        lider.aceitar_pedido(
            AceitarPedido(
                idPedido=id_pedido,
                idEntregador="entregador-1",
                timestamp=2,
            )
        )
    )

    run(
        lider.confirmar_entrega(
            ConfirmarEntrega(
                idPedido=id_pedido,
                idCliente="cliente-1",
                timestamp=3,
            )
        )
    )

    assert id_pedido not in lider.mapa_pedido_servidor
    assert id_pedido not in adms["adm-1"].mapa_pedido_servidor


def test_novo_lider_sincroniza_roteamento_dos_peers():
    router = ClusterRouter()
    adms = criar_cluster(["adm-1", "adm-2", "adm-3"], router)
    lider_antigo = adms["adm-3"]
    lider_antigo.lider_atual = "adm-3"
    id_pedido = uuid4()

    run(
        lider_antigo.criar_pedido(
            CriarPedido(
                idPedido=id_pedido,
                idCliente="cliente-1",
                idRestaurante="restaurante-1",
                timestamp=1,
            )
        )
    )
    _ativar_rastreadores(lider_antigo)
    pedido = run(
        lider_antigo.aceitar_pedido(
            AceitarPedido(
                idPedido=id_pedido,
                idEntregador="entregador-1",
                timestamp=2,
            )
        )
    )

    router.marcar_morto("adm-3")
    for adm in adms.values():
        adm.servidores_adm_ativos.discard("adm-3")
        adm.lider_atual = "adm-3"
        adm.id_lider_anterior = "adm-3"

    novo_lider = adms["adm-2"]
    novo_lider.mapa_pedido_servidor.clear()

    run(novo_lider.iniciar_eleicao())

    assert novo_lider.lider_atual == "adm-2"
    assert novo_lider.mapa_pedido_servidor[id_pedido] == pedido.servidorRastreadorResponsavel
    assert adms["adm-1"].mapa_pedido_servidor[id_pedido] == pedido.servidorRastreadorResponsavel


def test_replica_de_lider_antigo_e_ignorada():
    router = ClusterRouter()
    adms = criar_cluster(["adm-1", "adm-2"], router)
    adms["adm-2"].lider_atual = "adm-2"
    id_pedido = uuid4()

    run(
        adms["adm-1"].processar_replicacao_roteamento(
            ReplicacaoRoteamento(
                idServidorOrigem="adm-1",
                roteamento={str(id_pedido): "rastreador-1"},
                timestamp=1,
            )
        )
    )

    assert adms["adm-1"].mapa_pedido_servidor == {}


def test_novo_lider_confirma_entrega_apos_falha_do_lider():
    router = ClusterRouter()
    adms = criar_cluster(["adm-1", "adm-2", "adm-3"], router)
    lider_antigo = adms["adm-3"]
    lider_antigo.lider_atual = "adm-3"
    id_pedido = uuid4()

    run(
        lider_antigo.criar_pedido(
            CriarPedido(
                idPedido=id_pedido,
                idCliente="cliente-1",
                idRestaurante="restaurante-1",
                timestamp=1,
            )
        )
    )
    _ativar_rastreadores(lider_antigo)
    run(
        lider_antigo.aceitar_pedido(
            AceitarPedido(
                idPedido=id_pedido,
                idEntregador="entregador-1",
                timestamp=2,
            )
        )
    )

    router.marcar_morto("adm-3")
    for adm in adms.values():
        adm.servidores_adm_ativos.discard("adm-3")
        adm.lider_atual = "adm-3"
        adm.id_lider_anterior = "adm-3"

    novo_lider = adms["adm-2"]
    novo_lider.pedidos.clear()
    novo_lider.mapa_pedido_servidor.clear()

    run(novo_lider.iniciar_eleicao())

    assert id_pedido in novo_lider.pedidos
    run(
        novo_lider.confirmar_entrega(
            ConfirmarEntrega(
                idPedido=id_pedido,
                idCliente="cliente-1",
                timestamp=3,
            )
        )
    )
    assert id_pedido not in novo_lider.pedidos
