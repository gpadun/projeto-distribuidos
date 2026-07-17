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


class DriverBrokerError(RuntimeError):
    """Raised when the driver cannot accept an order through ADM."""


def parse_pedido_disponivel(payload: dict) -> PedidoDisponivel:
    """Validate broker payload as PedidoDisponivel."""
    return PedidoDisponivel.model_validate(payload)


def aceitar_pedido_via_adm(
    adm_url: str,
    id_entregador: str,
    id_pedido: UUID,
    timeout: float = 5.0,
) -> dict:
    """Send AceitarPedido to Adm leader over HTTP."""
    requisicao = AceitarPedido(
        idPedido=id_pedido,
        idEntregador=id_entregador,
        timestamp=int(time.time()),
    )
    url = f"{adm_url.rstrip('/')}/pedidos/aceitar"

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=to_message_dict(requisicao))

    if response.status_code == 200:
        return response.json()
    
    if response.status_code == 409:
        detail = response.json().get("detail", {})
        lider = detail.get("liderAtual", "?")
        raise DriverBrokerError(
            f"ADM em {adm_url} nao e o lider; lider atual: {lider}. "
            "Use a URL do lider em --adm-url."
        )
    
    raise DriverBrokerError(
        f"falha ao aceitar pedido: HTTP {response.status_code} - {response.text}"
    )


def parse_entrega_confirmada(payload: dict) -> EntregaConfirmada:
    """Validate broker payload as EntregaConfirmada."""
    return EntregaConfirmada.model_validate(payload)


def criar_callback_entrega_confirmada(
    parar_gps: dict[UUID, threading.Event],
):
    """Build the RabbitMQ callback that stops GPS publishing for one order."""

    def callback(payload: dict) -> None:
        evento = parse_entrega_confirmada(payload)
        parar = parar_gps.get(evento.idPedido)
        if parar is None:
            return
        parar.set()
        print(f"[entregador] entrega confirmada: idPedido={evento.idPedido}")

    return callback


def criar_callback_rastreador_atualizado(
    rastreador_por_pedido: dict[UUID, str],
):
    """Build the RabbitMQ callback that updates GPS routing after ADM failover."""

    def callback(payload: dict) -> None:
        id_pedido = UUID(str(payload["idPedido"]))
        novo_rastreador = payload["idServidorRastreador"]
        rastreador_por_pedido[id_pedido] = novo_rastreador
        print(
            f"[entregador] rastreador atualizado pedido={id_pedido} -> {novo_rastreador}"
        )

    return callback


def criar_callback_pedido_disponivel(
    id_entregador: str,
    adm_url: str,
    aceitar_automatico: bool,
    broker_settings: BrokerSettings,
    parar_gps: dict[UUID, threading.Event],
    rastreador_por_pedido: dict[UUID, str],
    intervalo_gps: float = 2.0,
):
    """Build the RabbitMQ callback for PedidoDisponivel events."""
    pedidos_aceitos: set[UUID] = set()

    def callback(payload: dict) -> None:
        evento = parse_pedido_disponivel(payload)
        print(
            f"[entregador] pedido disponivel: idPedido={evento.idPedido} "
            f"restaurante={evento.idRestaurante}"
        )

        if not aceitar_automatico:
            return
        
        if evento.idPedido in pedidos_aceitos:
            return
        
        resultado = aceitar_pedido_via_adm(adm_url, id_entregador, evento.idPedido)
        pedidos_aceitos.add(evento.idPedido)
        id_rastreador = resultado.get("servidorRastreadorResponsavel")
        print(
            f"[entregador] pedido aceito: idPedido={resultado.get('idPedido')} "
            f"rastreador={id_rastreador}"
        )

        if not id_rastreador:
            return

        parar = threading.Event()
        parar_gps[evento.idPedido] = parar
        rastreador_por_pedido[evento.idPedido] = id_rastreador

        thread = threading.Thread(
            target=_publicar_localizacoes_periodicas,
            args=(
                id_entregador,
                evento.idPedido,
                intervalo_gps,
                broker_settings,
                parar,
                rastreador_por_pedido,
            ),
            daemon=True,
        )
        thread.start()

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

    callback = criar_callback_pedido_disponivel(
        id_entregador=id_entregador,
        adm_url=adm_url,
        aceitar_automatico=aceitar_automatico,
        broker_settings=settings,
        parar_gps=parar_gps,
        rastreador_por_pedido=rastreador_por_pedido,
        intervalo_gps=intervalo_gps,
    )

    subscriber.subscribe(EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL, callback)
    subscriber.subscribe(
        EXCHANGE_PEDIDOS,
        ROUTING_ENTREGA_CONFIRMADA,
        criar_callback_entrega_confirmada(parar_gps),
    )
    subscriber.subscribe(
        EXCHANGE_PEDIDOS,
        ROUTING_RASTREADOR_ATUALIZADO,
        criar_callback_rastreador_atualizado(rastreador_por_pedido),
    )
    print(
        f"[entregador] ouvindo {EXCHANGE_PEDIDOS}/{ROUTING_PEDIDO_DISPONIVEL}, "
        f"{EXCHANGE_PEDIDOS}/{ROUTING_ENTREGA_CONFIRMADA}, "
        f"{EXCHANGE_PEDIDOS}/{ROUTING_RASTREADOR_ATUALIZADO} "
        f"como {id_entregador}; ADM={adm_url}"
    )

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
            print(
                f"[entregador] localizacao enviada pedido={id_pedido} "
                f"rastreador={id_rastreador}"
            )
            if parar_event.wait(timeout=intervalo_segundos):
                break
    except Exception as exc:
        print(f"[entregador] erro ao publicar localizacao: {exc}")
    finally:
        fechar_publisher(publisher)
        if parar_event.is_set():
            print(f"[entregador] GPS encerrado para pedido={id_pedido}")
