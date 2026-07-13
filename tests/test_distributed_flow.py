"""End-to-end tests for the in-memory distributed system proof of concept."""

import asyncio
from time import time
from uuid import uuid4

import pytest

from src.core.models import (
    AceitarPedido,
    ConfirmarEntrega,
    CriarPedido,
    KeepAlive,
    LocalizacaoEntregador,
    TipoServidor,
    IniciarEleicao,
    RespostaEleicao,
    NovoLider,
)
from src.servers.adm_server import ADMServer
from src.servers.support_server import SupportServer
from src.servers.tracker_server import TrackerServer


class RecordingPublisher:
    def __init__(self):
        self.messages = []

    def publish(self, exchange: str, routing_key: str, message: dict) -> None:
        self.messages.append(
            {"exchange": exchange, "routing_key": routing_key, "message": message}
        )


class ElectionRouter:
    def __init__(self):
        self.adms: dict[str, ADMServer] = {}
        self.mortos: set[str] = set()

    def registrar(self, adm: ADMServer) -> None:
        self.adms[adm.id_servidor] = adm

    def marcar_morto(self, id_adm: str) -> None:
        self.mortos.add(id_adm)
        self.adms.pop(id_adm, None)

    async def enviar(self, id_destino: str, mensagem) -> None:
        if id_destino in self.mortos:
            return

        destino = self.adms[id_destino]

        if isinstance(mensagem, IniciarEleicao):
            await destino.processar_iniciar_eleicao(mensagem)
        elif isinstance(mensagem, RespostaEleicao):
            await destino.processar_resposta_eleicao(mensagem)
        elif isinstance(mensagem, NovoLider):
            await destino.processar_novo_lider(mensagem)


def criar_cluster_adm(ids: list[str], router: ElectionRouter) -> dict[str, ADMServer]:
    adms = {}
    for id_adm in ids:
        adm = ADMServer(
            id_servidor=id_adm,
            servidores_adm=ids,
            election_sender=router.enviar,
            eleicao_timeout=0.2,
        )
        router.registrar(adm)
        adms[id_adm] = adm
    return adms


def run(coro):
    return asyncio.run(coro)


def test_fluxo_criar_aceitar_rastrear_confirmar():
    publisher = RecordingPublisher()
    adm = ADMServer("adm-1", ["rastreador-1", "rastreador-2"], publisher=publisher)
    support = SupportServer("sup-1", "rastreador-1")
    tracker = TrackerServer("rastreador-1", publisher=publisher, support_server=support)
    id_pedido = uuid4()

    pedido = run(
        adm.criar_pedido(
            CriarPedido(
                idPedido=id_pedido,
                idCliente="cliente-1",
                idRestaurante="restaurante-1",
                timestamp=1710000000,
            )
        )
    )
    assert pedido.idPedido == id_pedido
    assert id_pedido in adm.pedidos_sem_entregador

    pedido = run(
        adm.aceitar_pedido(
            AceitarPedido(
                idPedido=id_pedido,
                idEntregador="entregador-1",
                timestamp=1710000001,
            )
        )
    )
    assert pedido.idEntregador == "entregador-1"
    assert pedido.servidorRastreadorResponsavel in {"rastreador-1", "rastreador-2"}

    run(tracker.registrar_entregador("entregador-1", id_pedido))
    run(
        tracker.receber_localizacao(
            LocalizacaoEntregador(
                idEntregador="entregador-1",
                idPedido=id_pedido,
                latitude=-23.55,
                longitude=-46.63,
                timestamp=1710000002,
            )
        )
    )
    assert str(id_pedido) in run(support.enviar_lista_backup())

    evento = run(
        adm.confirmar_entrega(
            ConfirmarEntrega(
                idPedido=id_pedido,
                idCliente="cliente-1",
                timestamp=1710000003,
            )
        )
    )
    assert evento.idPedido == id_pedido
    assert id_pedido not in adm.pedidos

    routing_keys = {message["routing_key"] for message in publisher.messages}
    assert "pedido.disponivel" in routing_keys
    assert f"pedido.{id_pedido}" in routing_keys
    assert f"pedido.{id_pedido}.entrega_confirmada" in routing_keys


def test_tracker_ignora_localizacao_antiga():
    tracker = TrackerServer("rastreador-1")
    id_pedido = uuid4()
    run(tracker.registrar_entregador("entregador-1", id_pedido))

    nova = LocalizacaoEntregador(
        idEntregador="entregador-1",
        idPedido=id_pedido,
        latitude=-23.55,
        longitude=-46.63,
        timestamp=20,
    )
    antiga = LocalizacaoEntregador(
        idEntregador="entregador-1",
        idPedido=id_pedido,
        latitude=-1,
        longitude=-1,
        timestamp=10,
    )

    run(tracker.receber_localizacao(nova))
    run(tracker.receber_localizacao(antiga))

    assert tracker.ultimas_localizacoes[id_pedido].latitude == -23.55


def test_tracker_rejeita_localizacao_de_pedido_desconhecido():
    tracker = TrackerServer("rastreador-1")

    with pytest.raises(ValueError, match="pedido nao registrado"):
        run(
            tracker.receber_localizacao(
                LocalizacaoEntregador(
                    idEntregador="entregador-1",
                    idPedido=uuid4(),
                    latitude=-23.55,
                    longitude=-46.63,
                    timestamp=20,
                )
            )
        )


def test_adm_detecta_heartbeat_expirado_e_redistribui():
    support = SupportServer("sup-1", "rastreador-1")
    adm = ADMServer(
        "adm-1",
        ["rastreador-1", "rastreador-2"],
        support_servers={"rastreador-1": support},
        heartbeat_timeout=5,
    )
    id_pedido = uuid4()

    run(
        adm.criar_pedido(
            CriarPedido(
                idPedido=id_pedido,
                idCliente="cliente-1",
                idRestaurante="restaurante-1",
                timestamp=1,
            )
        )
    )
    adm.mapa_pedido_servidor[id_pedido] = "rastreador-1"
    adm.pedidos[id_pedido].servidorRastreadorResponsavel = "rastreador-1"
    adm.ultimo_keepalive["rastreador-1"] = time() - 10

    assert adm.servidores_com_heartbeat_expirado()
    redistribuidos = run(adm.detectar_falha_servidor_rastreador("rastreador-1"))

    assert redistribuidos[id_pedido] == "rastreador-2"
    assert adm.mapa_pedido_servidor[id_pedido] == "rastreador-2"


def test_adm_expira_rastreador_que_nunca_renovou_heartbeat():
    adm = ADMServer("adm-1", ["rastreador-1"], heartbeat_timeout=5)

    assert adm.servidores_com_heartbeat_expirado(agora=time() + 10) == ["rastreador-1"]


def test_adm_retorna_heartbeats_expirados_em_ordem_estavel():
    adm = ADMServer("adm-1", ["rastreador-2", "rastreador-1"], heartbeat_timeout=5)

    assert adm.servidores_com_heartbeat_expirado(agora=time() + 10) == [
        "rastreador-1",
        "rastreador-2",
    ]


def test_adm_usa_tempo_local_para_keepalive():
    adm = ADMServer("adm-1", ["rastreador-1"])

    run(
        adm.processar_keepalive(
            KeepAlive(idServidor="rastreador-1", tipoServidor="RASTREADOR", timestamp=9999999999)
        )
    )

    assert abs(adm.ultimo_keepalive["rastreador-1"] - time()) < 2


def test_adm_ignora_chave_invalida_no_backup_do_sup():
    support = SupportServer("sup-1", "rastreador-1")
    support.rastreios = {"nao-e-uuid": {"idEntregador": "entregador-1"}}
    adm = ADMServer(
        "adm-1",
        ["rastreador-1", "rastreador-2"],
        support_servers={"rastreador-1": support},
    )

    redistribuidos = run(adm.detectar_falha_servidor_rastreador("rastreador-1"))

    assert redistribuidos == {}


def test_bully_algorithm_usa_sufixo_numerico_do_id():
    assert ADMServer._maior_id(["adm-1", "adm-2", "adm-10"]) == "adm-10"


def test_adm_keepalive_marca_adm_como_ativo():
    adm = ADMServer("adm-1", servidores_adm=["adm-1", "adm-2"])
    adm.servidores_adm_ativos.discard("adm-2")

    run(adm.processar_keepalive(
        KeepAlive(idServidor="adm-2", tipoServidor=TipoServidor.ADM, timestamp=1)
    ))

    assert "adm-2" in adm.servidores_adm_ativos


def test_adm_executar_ciclo_keepalive_envia_para_peers():
    envios = []

    async def fake_sender(id_destino, mensagem):
        envios.append(id_destino)

    adm = ADMServer(
        "adm-1",
        servidores_adm=["adm-1", "adm-2", "adm-3"],
        keepalive_sender=fake_sender,
    )

    run(adm.executar_ciclo_keepalive())

    assert sorted(envios) == ["adm-2", "adm-3"]


def test_adm_detecta_falha_do_lider_remoto():
    adm = ADMServer(
        "adm-1",
        servidores_adm=["adm-1", "adm-2", "adm-3"],
        heartbeat_timeout=5,
    )
    adm.lider_atual = "adm-3"
    adm.ultimo_keepalive["adm-3"] = time() - 10

    falha = run(adm.detectar_falha_lider())

    assert falha is True
    assert adm.lider_disponivel is False
    assert adm.aguardando_eleicao is True
    assert adm.id_lider_anterior == "adm-3"
    assert "adm-3" not in adm.servidores_adm_ativos


def test_adm_nao_detecta_falha_quando_eu_sou_lider():
    adm = ADMServer("adm-3", servidores_adm=["adm-1", "adm-2", "adm-3"])
    adm.lider_atual = "adm-3"
    adm.ultimo_keepalive["adm-3"] = time() - 100  # mesmo expirado

    falha = run(adm.detectar_falha_lider())

    assert falha is False
    assert adm.lider_disponivel is True


def test_adm_nao_detecta_falha_com_lider_vivo():
    adm = ADMServer("adm-1", servidores_adm=["adm-1", "adm-2", "adm-3"])
    adm.lider_atual = "adm-3"

    run(adm.processar_keepalive(
        KeepAlive(idServidor="adm-3", tipoServidor=TipoServidor.ADM, timestamp=1)
    ))

    falha = run(adm.detectar_falha_lider())

    assert falha is False
    assert adm.lider_disponivel is True


def test_adm_ciclo_monitoramento_detecta_falha_lider():
    adm = ADMServer(
        "adm-1",
        servidores_adm=["adm-1", "adm-2", "adm-3"],
        heartbeat_timeout=5,
    )
    adm.lider_atual = "adm-3"
    adm.ultimo_keepalive["adm-3"] = time() - 10

    falha = run(adm.executar_ciclo_monitoramento())

    assert falha is True
    assert adm.aguardando_eleicao is True


def test_adm_chama_callback_quando_lider_cai():
    chamadas = []

    async def on_lider_caiu(id_lider):
        chamadas.append(id_lider)

    adm = ADMServer(
        "adm-1",
        servidores_adm=["adm-1", "adm-2", "adm-3"],
        heartbeat_timeout=5,
        on_lider_caiu=on_lider_caiu,
    )
    adm.lider_atual = "adm-3"
    adm.ultimo_keepalive["adm-3"] = time() - 10

    run(adm.detectar_falha_lider())

    assert chamadas == ["adm-3"]


def test_bully_maior_id_ativo_vira_lider():
    router = ElectionRouter()
    adms = criar_cluster_adm(["adm-1", "adm-2", "adm-3"], router)

    # adm-3 era líder e "caiu"
    for adm in adms.values():
        adm.servidores_adm_ativos.discard("adm-3")
    adms["adm-1"].lider_atual = "adm-3"
    adms["adm-1"].id_lider_anterior = "adm-3"
    adms["adm-1"].aguardando_eleicao = True

    lider = run(adms["adm-1"].iniciar_eleicao())

    assert lider == "adm-2"  # adm-3 fora, adm-2 é o maior ativo
    assert adms["adm-1"].lider_atual == "adm-2"
    assert adms["adm-2"].lider_atual == "adm-2"


def test_bully_iniciador_desiste_quando_maior_responde():
    router = ElectionRouter()
    adms = criar_cluster_adm(["adm-1", "adm-2", "adm-3"], router)

    # adm-3 "caiu" em todo o cluster
    for adm in adms.values():
        adm.servidores_adm_ativos.discard("adm-3")
        adm.lider_atual = "adm-3"
        adm.id_lider_anterior = "adm-3"

    run(adms["adm-1"].iniciar_eleicao())

    assert adms["adm-1"].recebeu_resposta_de_maior is True
    assert adms["adm-1"].eleicao_em_andamento is False
    assert adms["adm-2"].lider_atual == "adm-2"
    assert adms["adm-1"].lider_atual == "adm-2"  # recebeu NovoLider do adm-2


def test_bully_sem_maiores_ativos_torna_se_lider():
    adm = ADMServer("adm-10", servidores_adm=["adm-1", "adm-10"], eleicao_timeout=0.2)
    adm.servidores_adm_ativos = {"adm-10"}  # só eu

    lider = run(adm.iniciar_eleicao())

    assert lider == "adm-10"
    assert adm.lider_disponivel is True


def test_bully_novo_lider_atualiza_peers():
    router = ElectionRouter()
    adms = criar_cluster_adm(["adm-1", "adm-2"], router)

    run(adms["adm-2"].processar_novo_lider(
        NovoLider(idServidor="adm-2", timestamp=1)
    ))

    assert adms["adm-1"].lider_atual == "adm-2"
    assert adms["adm-1"].aguardando_eleicao is False


def test_bully_eleicao_apos_falha_do_lider():
    router = ElectionRouter()
    adms = criar_cluster_adm(["adm-1", "adm-2", "adm-3"], router)

    for adm in adms.values():
        adm.lider_atual = "adm-3"
        adm.ultimo_keepalive["adm-3"] = time() - 100
        adm.servidores_adm_ativos.discard("adm-3")  # reforço explícito

    router.marcar_morto("adm-3")  # use marcar_morto, não só pop

    run(adms["adm-1"].detectar_falha_lider())
    run(adms["adm-1"].iniciar_eleicao())

    assert adms["adm-1"].lider_atual == "adm-2"
    assert adms["adm-2"].lider_atual == "adm-2"
    assert adms["adm-1"].aguardando_eleicao is False


def test_bully_eleicao_disparada_por_callback():
    router = ElectionRouter()
    adms = criar_cluster_adm(["adm-1", "adm-2", "adm-3"], router)

    # Define callback DEPOIS de criar adm-1, ou reatribui:
    async def on_lider_caiu(id_lider):
        await adms["adm-1"].iniciar_eleicao()

    adms["adm-1"].on_lider_caiu = on_lider_caiu

    for adm in adms.values():
        adm.servidores_adm_ativos.discard("adm-3")

    adms["adm-1"].lider_atual = "adm-3"
    adms["adm-1"].ultimo_keepalive["adm-3"] = time() - 10

    run(adms["adm-1"].detectar_falha_lider())

    assert adms["adm-1"].lider_atual == "adm-2"
    assert adms["adm-1"].aguardando_eleicao is False