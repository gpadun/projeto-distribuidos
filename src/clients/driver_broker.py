"""Driver client that listens to PedidoDisponivel on RabbitMQ."""

import os
import random
import threading
import time
from uuid import UUID

import httpx

from src.broker.config import BrokerSettings
from src.broker.factory import (
    criar_publisher,
    criar_subscriber,
    fechar_publisher,
    fechar_subscriber,
)
from src.broker.topology import (
    EXCHANGE_LOCALIZACAO,
    EXCHANGE_PEDIDOS,
    ROUTING_ENTREGA_CONFIRMADA,
    ROUTING_PEDIDO_DISPONIVEL,
    ROUTING_RASTREADOR_ATUALIZADO,
    routing_localizacao_para_rastreador,
)
from src.core.models import (
    AceitarPedido,
    EntregaConfirmada,
    LocalizacaoEntregador,
    PedidoDisponivel,
)
from src.core.serialization import to_message_dict
from src.infra.adm_lider import carregar_adm_urls, resolver_adm_lider_url, url_do_adm
from src.presentation_log import log_apresentacao


class DriverBrokerError(RuntimeError):
    """Raised when the driver cannot accept an order through ADM."""


class PedidoJaAceitoError(DriverBrokerError):
    """Raised when another driver already accepted the order."""


def entregador_tem_entrega_ativa(parar_gps: dict[UUID, threading.Event]) -> bool:
    """Return True when the driver still has at least one active delivery."""
    return any(not event.is_set() for event in parar_gps.values())


def parse_pedido_disponivel(payload: dict) -> PedidoDisponivel:
    """Validate broker payload as PedidoDisponivel."""
    return PedidoDisponivel.model_validate(payload)


def listar_pedidos_sem_entregador_via_adm(
    adm_url: str,
    timeout: float = 5.0,
    adm_urls: list[str] | None = None,
) -> list[UUID]:
    """Return orders waiting for a driver according to the ADM leader state."""
    urls_candidatas = adm_urls or carregar_adm_urls()
    url_atual = resolver_adm_lider_url(adm_url=adm_url, adm_urls=urls_candidatas, timeout=timeout)

    tentativas = [url_atual]
    for url in urls_candidatas:
        if url not in tentativas:
            tentativas.append(url)

    ultimo_erro: Exception | None = None
    indice = 0
    while indice < len(tentativas):
        url = tentativas[indice]
        indice += 1
        endpoint = f"{url.rstrip('/')}/estado"
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(endpoint)
        except httpx.HTTPError as exc:
            ultimo_erro = DriverBrokerError(
                f"falha ao consultar pedidos pendentes no ADM em {url}: {exc}"
            )
            continue

        if response.status_code == 200:
            body = response.json()
            return [UUID(str(id_pedido)) for id_pedido in body.get("pedidosSemEntregador", [])]

        ultimo_erro = DriverBrokerError(
            f"falha ao consultar pedidos pendentes: HTTP {response.status_code} - {response.text}"
        )

    if ultimo_erro is None:
        raise DriverBrokerError("nenhum ADM disponivel para consultar pedidos pendentes")
    raise ultimo_erro


def aceitar_pedido_via_adm(
    adm_url: str,
    id_entregador: str,
    id_pedido: UUID,
    timeout: float = 5.0,
    adm_urls: list[str] | None = None,
) -> dict:
    """Send AceitarPedido to the ADM leader, rediscovering it when needed."""
    urls_candidatas = adm_urls or carregar_adm_urls()
    url_atual = resolver_adm_lider_url(adm_url=adm_url, adm_urls=urls_candidatas, timeout=timeout)

    requisicao = AceitarPedido(
        idPedido=id_pedido,
        idEntregador=id_entregador,
        timestamp=int(time.time()),
    )
    payload = to_message_dict(requisicao)

    tentativas = [url_atual]
    for url in urls_candidatas:
        if url not in tentativas:
            tentativas.append(url)

    ultimo_erro: Exception | None = None
    indice = 0
    while indice < len(tentativas):
        url = tentativas[indice]
        indice += 1
        endpoint = f"{url.rstrip('/')}/pedidos/aceitar"
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(endpoint, json=payload)
        except httpx.HTTPError as exc:
            ultimo_erro = DriverBrokerError(
                f"falha ao contactar ADM em {url}: {exc}"
            )
            continue

        if response.status_code == 200:
            return response.json()

        if response.status_code == 409:
            detail = response.json().get("detail", {})
            if detail.get("motivo") == "pedido_ja_aceito":
                raise PedidoJaAceitoError(
                    f"pedido ja aceito por {detail.get('idEntregadorAtual', '?')}"
                )
            id_lider = detail.get("liderAtual")
            url_lider = url_do_adm(id_lider, urls_candidatas) if id_lider else None
            if url_lider and url_lider not in tentativas:
                tentativas.append(url_lider)
            ultimo_erro = DriverBrokerError(
                f"ADM em {url} nao e o lider; lider atual: {id_lider or '?'}"
            )
            continue

        ultimo_erro = DriverBrokerError(
            f"falha ao aceitar pedido: HTTP {response.status_code} - {response.text}"
        )

    if ultimo_erro is None:
        raise DriverBrokerError("nenhum ADM disponivel para aceitar o pedido")
    raise ultimo_erro


def parse_entrega_confirmada(payload: dict) -> EntregaConfirmada:
    """Validate broker payload as EntregaConfirmada."""
    return EntregaConfirmada.model_validate(payload)


def _iniciar_gps_pedido(
    id_entregador: str,
    id_pedido: UUID,
    id_rastreador: str,
    broker_settings: BrokerSettings,
    parar_gps: dict[UUID, threading.Event],
    rastreador_por_pedido: dict[UUID, str],
    intervalo_gps: float,
) -> None:
    parar = threading.Event()
    parar_gps[id_pedido] = parar
    rastreador_por_pedido[id_pedido] = id_rastreador
    thread = threading.Thread(
        target=_publicar_localizacoes_periodicas,
        args=(
            id_entregador,
            id_pedido,
            intervalo_gps,
            broker_settings,
            parar,
            rastreador_por_pedido,
        ),
        daemon=True,
    )
    thread.start()


def _aceitar_e_iniciar_entrega(
    id_entregador: str,
    adm_url: str,
    id_pedido: UUID,
    pedidos_aceitos: set[UUID],
    broker_settings: BrokerSettings,
    parar_gps: dict[UUID, threading.Event],
    rastreador_por_pedido: dict[UUID, str],
    intervalo_gps: float,
) -> bool:
    """Try to accept one order and start GPS. Returns True when delivery started."""
    if id_pedido in pedidos_aceitos:
        return False
    if entregador_tem_entrega_ativa(parar_gps):
        return False

    try:
        resultado = aceitar_pedido_via_adm(
            adm_url,
            id_entregador,
            id_pedido,
            adm_urls=carregar_adm_urls(),
        )
    except PedidoJaAceitoError:
        return False
    except DriverBrokerError as exc:
        log_apresentacao("entregador", f"erro ao aceitar pedido: {exc}")
        return False

    pedidos_aceitos.add(id_pedido)
    id_rastreador = resultado.get("servidorRastreadorResponsavel")
    log_apresentacao(
        "entregador",
        f"pedido aceito: idPedido={resultado.get('idPedido')} rastreador={id_rastreador}",
    )
    if not id_rastreador:
        return False

    _iniciar_gps_pedido(
        id_entregador,
        id_pedido,
        id_rastreador,
        broker_settings,
        parar_gps,
        rastreador_por_pedido,
        intervalo_gps,
    )
    return True


def tentar_aceitar_pedidos_pendentes(
    id_entregador: str,
    adm_url: str,
    aceitar_automatico: bool,
    pedidos_aceitos: set[UUID],
    broker_settings: BrokerSettings,
    parar_gps: dict[UUID, threading.Event],
    rastreador_por_pedido: dict[UUID, str],
    intervalo_gps: float,
) -> None:
    """Pick up orders still waiting on ADM when this driver becomes idle."""
    if not aceitar_automatico or entregador_tem_entrega_ativa(parar_gps):
        return

    try:
        pendentes = listar_pedidos_sem_entregador_via_adm(
            adm_url,
            adm_urls=carregar_adm_urls(),
        )
    except DriverBrokerError as exc:
        log_apresentacao("entregador", f"erro ao consultar fila de pedidos: {exc}")
        return

    for id_pedido in pendentes:
        if _aceitar_e_iniciar_entrega(
            id_entregador,
            adm_url,
            id_pedido,
            pedidos_aceitos,
            broker_settings,
            parar_gps,
            rastreador_por_pedido,
            intervalo_gps,
        ):
            log_apresentacao(
                "entregador",
                f"pedido pendente assumido da fila: idPedido={id_pedido}",
            )
            return


def criar_callback_entrega_confirmada(
    id_entregador: str,
    adm_url: str,
    aceitar_automatico: bool,
    pedidos_aceitos: set[UUID],
    broker_settings: BrokerSettings,
    parar_gps: dict[UUID, threading.Event],
    rastreador_por_pedido: dict[UUID, str],
    intervalo_gps: float,
):
    """Build the RabbitMQ callback that stops GPS publishing for one order."""

    def callback(payload: dict) -> None:
        evento = parse_entrega_confirmada(payload)
        parar = parar_gps.get(evento.idPedido)
        if parar is None:
            return
        parar.set()
        rastreador_por_pedido.pop(evento.idPedido, None)
        log_apresentacao("entregador", f"entrega confirmada: idPedido={evento.idPedido}")
        tentar_aceitar_pedidos_pendentes(
            id_entregador,
            adm_url,
            aceitar_automatico,
            pedidos_aceitos,
            broker_settings,
            parar_gps,
            rastreador_por_pedido,
            intervalo_gps,
        )

    return callback


def criar_callback_rastreador_atualizado(
    rastreador_por_pedido: dict[UUID, str],
    parar_gps: dict[UUID, threading.Event],
):
    """Build the RabbitMQ callback that updates GPS routing after ADM failover."""

    def callback(payload: dict) -> None:
        id_pedido = UUID(str(payload["idPedido"]))
        parar = parar_gps.get(id_pedido)
        if parar is None or parar.is_set():
            return

        novo_rastreador = payload["idServidorRastreador"]
        rastreador_por_pedido[id_pedido] = novo_rastreador
        log_apresentacao(
            "entregador",
            f"rastreador atualizado pedido={id_pedido} -> {novo_rastreador}",
        )

    return callback


def criar_callback_pedido_disponivel(
    id_entregador: str,
    adm_url: str,
    aceitar_automatico: bool,
    pedidos_aceitos: set[UUID],
    broker_settings: BrokerSettings,
    parar_gps: dict[UUID, threading.Event],
    rastreador_por_pedido: dict[UUID, str],
    intervalo_gps: float = 2.0,
):
    """Build the RabbitMQ callback for PedidoDisponivel events."""

    def callback(payload: dict) -> None:
        evento = parse_pedido_disponivel(payload)
        log_apresentacao(
            "entregador",
            f"pedido disponivel: idPedido={evento.idPedido} restaurante={evento.idRestaurante}",
        )

        if not aceitar_automatico:
            return

        if entregador_tem_entrega_ativa(parar_gps):
            log_apresentacao(
                "entregador",
                f"pedido em espera no ADM (ocupado): idPedido={evento.idPedido}",
            )
            return

        aceito = _aceitar_e_iniciar_entrega(
            id_entregador,
            adm_url,
            evento.idPedido,
            pedidos_aceitos,
            broker_settings,
            parar_gps,
            rastreador_por_pedido,
            intervalo_gps,
        )
        if not aceito and evento.idPedido not in pedidos_aceitos:
            log_apresentacao(
                "entregador",
                f"pedido ja aceito por outro: idPedido={evento.idPedido}",
            )

    return callback


def executar_entregador_broker(
        id_entregador: str,
        adm_url: str | None = None,
        aceitar_automatico: bool = True,
        broker_settings: BrokerSettings | None = None,
        intervalo_gps: float = 2.0,
) -> None:
    """Subscribe to PedidoDisponivel and block until interrupted."""
    settings = broker_settings or BrokerSettings.from_env()
    if not settings.enabled:
        raise DriverBrokerError(
            "RabbitMQ desabilitado. Defina RABBITMQ_ENABLED=1 antes de subir o entregador."
        )
    
    adm_url = adm_url or os.getenv("ADM_URL", "http://127.0.0.1:8003")
    subscriber = criar_subscriber(settings)
    if subscriber is None:
        raise DriverBrokerError("nao foi possivel criar subscriber RabbitMQ")

    parar_gps: dict[UUID, threading.Event] = {}
    rastreador_por_pedido: dict[UUID, str] = {}
    pedidos_aceitos: set[UUID] = set()

    callback = criar_callback_pedido_disponivel(
        id_entregador=id_entregador,
        adm_url=adm_url,
        aceitar_automatico=aceitar_automatico,
        pedidos_aceitos=pedidos_aceitos,
        broker_settings=settings,
        parar_gps=parar_gps,
        rastreador_por_pedido=rastreador_por_pedido,
        intervalo_gps=intervalo_gps,
    )

    subscriber.subscribe(EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL, callback)
    subscriber.subscribe(
        EXCHANGE_PEDIDOS,
        ROUTING_ENTREGA_CONFIRMADA,
        criar_callback_entrega_confirmada(
            id_entregador,
            adm_url,
            aceitar_automatico,
            pedidos_aceitos,
            settings,
            parar_gps,
            rastreador_por_pedido,
            intervalo_gps,
        ),
    )
    subscriber.subscribe(
        EXCHANGE_PEDIDOS,
        ROUTING_RASTREADOR_ATUALIZADO,
        criar_callback_rastreador_atualizado(rastreador_por_pedido, parar_gps),
    )
    print(
        f"[entregador] ouvindo {EXCHANGE_PEDIDOS}/{ROUTING_PEDIDO_DISPONIVEL}, "
        f"{EXCHANGE_PEDIDOS}/{ROUTING_ENTREGA_CONFIRMADA}, "
        f"{EXCHANGE_PEDIDOS}/{ROUTING_RASTREADOR_ATUALIZADO} "
        f"como {id_entregador}; ADM={adm_url}"
    )

    if aceitar_automatico:
        threading.Thread(
            target=tentar_aceitar_pedidos_pendentes,
            args=(
                id_entregador,
                adm_url,
                aceitar_automatico,
                pedidos_aceitos,
                settings,
                parar_gps,
                rastreador_por_pedido,
                intervalo_gps,
            ),
            daemon=True,
        ).start()

    try:
        subscriber.start_consuming()
    except KeyboardInterrupt:
        print("[entregador] encerrando...")
    finally:
        fechar_subscriber(subscriber)


def _publicar_localizacoes_periodicas(
    id_entregador: str,
    id_pedido: UUID,
    intervalo_segundos: float,
    broker_settings: BrokerSettings,
    parar_event: threading.Event,
    rastreador_por_pedido: dict[UUID, str],
) -> None:
    publisher = criar_publisher(broker_settings)
    if publisher is None:
        return

    latitude = -23.55052
    longitude = -46.633308
    primeira_localizacao = True

    try:
        while not parar_event.is_set():
            id_rastreador = rastreador_por_pedido.get(id_pedido)
            if not id_rastreador:
                if parar_event.wait(timeout=intervalo_segundos):
                    break
                continue

            latitude += random.uniform(-0.001, 0.001)
            longitude += random.uniform(-0.001, 0.001)
            localizacao = LocalizacaoEntregador(
                idEntregador=id_entregador,
                idPedido=id_pedido,
                latitude=round(latitude, 6),
                longitude=round(longitude, 6),
                timestamp=int(time.time()),
            )
            publisher.publish(
                EXCHANGE_LOCALIZACAO,
                routing_localizacao_para_rastreador(id_rastreador),
                to_message_dict(localizacao),
            )
            if primeira_localizacao:
                log_apresentacao(
                    "entregador",
                    f"localizacao enviada: pedido={id_pedido} rastreador={id_rastreador}",
                )
                primeira_localizacao = False
            if parar_event.wait(timeout=intervalo_segundos):
                break
    except Exception as exc:
        print(f"[entregador] erro ao publicar localizacao: {exc}")
    finally:
        fechar_publisher(publisher)
        if parar_event.is_set():
            print(f"[entregador] GPS encerrado para pedido={id_pedido}")
