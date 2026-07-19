"""Customer client that creates orders via HTTP and tracks delivery on RabbitMQ."""

import os
from time import time
from uuid import UUID, uuid4

import httpx

from src.broker.config import BrokerSettings
from src.broker.factory import criar_subscriber, fechar_subscriber
from src.broker.subscriber import Subscriber
from src.broker.topology import (
    EXCHANGE_PEDIDOS,
    EXCHANGE_RASTREIO,
    routing_entrega_confirmada,
    routing_localizacao,
)
from src.core.models import ConfirmarEntrega, CriarPedido, EntregaConfirmada, EventoLocalizacao
from src.core.serialization import to_message_dict
from src.presentation_log import log_apresentacao


class CustomerBrokerError(RuntimeError):
    """Raised when the customer cannot talk to ADM or RabbitMQ."""


def parse_evento_localizacao(payload: dict) -> EventoLocalizacao:
    """Validate broker payload as EventoLocalizacao."""
    return EventoLocalizacao.model_validate(payload)


def parse_entrega_confirmada(payload: dict) -> EntregaConfirmada:
    """Validate broker payload as EntregaConfirmada."""
    return EntregaConfirmada.model_validate(payload)


def criar_pedido_via_adm(
    adm_url: str,
    id_cliente: str,
    id_restaurante: str,
    id_pedido: UUID | None = None,
    timeout: float = 5.0,
) -> UUID:
    """Create an order on the ADM leader over HTTP."""
    pedido_id = id_pedido or uuid4()
    requisicao = CriarPedido(
        idPedido=pedido_id,
        idCliente=id_cliente,
        idRestaurante=id_restaurante,
        timestamp=int(time()),
    )
    url = f"{adm_url.rstrip('/')}/pedidos"

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=to_message_dict(requisicao))

    if response.status_code == 200:
        body = response.json()
        return UUID(str(body.get("idPedido", pedido_id)))
    
    if response.status_code == 409:
        detail = response.json().get("detail", {})
        lider = detail.get("liderAtual", "?")
        raise CustomerBrokerError(
            f"ADM em {adm_url} nao e o lider; lider atual: {lider}. "
            "Use a URL do lider em --adm-url."
        )
    
    raise CustomerBrokerError(
        f"falha ao criar pedido: HTTP {response.status_code} - {response.text}"
    )


def confirmar_entrega_via_adm(
        adm_url: str,
        id_cliente: str,
        id_pedido: UUID,
        timeout: float = 5.0,
) -> dict:
    """Confirm delivery on the ADM leader over HTTP."""
    requisicao = ConfirmarEntrega(
        idPedido=id_pedido,
        idCliente=id_cliente,
        timestamp=int(time()),
    )
    url = f"{adm_url.rstrip('/')}/pedidos/confirmar"

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=to_message_dict(requisicao))

    if response.status_code == 200:
        return response.json()
    
    if response.status_code == 409:
        detail = response.json().get("detail", {})
        lider = detail.get("liderAtual", "?")
        raise CustomerBrokerError(
            f"ADM em {adm_url} nao e o lider; lider atual: {lider}. "
            "Use a URL do lider em --adm-url."
        )
    
    raise CustomerBrokerError(
        f"falha ao confirmar entrega: HTTP {response.status_code} - {response.text}"
    )


def criar_callback_localizacao(id_cliente: str):
    """Build the RabbitMQ callback for EventoLocalizacao events."""

    def callback(payload: dict) -> None:
        evento = parse_evento_localizacao(payload)
        log_apresentacao(
            f"cliente {id_cliente}",
            f"localizacao: pedido={evento.idPedido} "
            f"lat={evento.latitude} lon={evento.longitude} ts={evento.timestamp}",
        )

    return callback


def criar_callback_entrega_confirmada(
    id_cliente: str,
    subscriber: Subscriber,
):
    """Build the RabbitMQ callback that ends tracking after delivery confirmation."""

    def callback(payload: dict) -> None:
        evento = parse_entrega_confirmada(payload)
        log_apresentacao(
            f"cliente {id_cliente}",
            f"entrega confirmada: pedido={evento.idPedido}",
        )
        print("[cliente] rastreio encerrado.")
        subscriber.stop_consuming()

    return callback


def executar_assinatura_rastreio(
    id_pedido: UUID,
    id_cliente: str,
    broker_settings: BrokerSettings | None = None,
) -> None:
    """Subscribe to EventoLocalizacao for one order and block until interrupted."""
    settings = broker_settings or BrokerSettings.from_env()
    if not settings.enabled:
        raise CustomerBrokerError(
            "RabbitMQ desabilitado. Defina RABBITMQ_ENABLED=1 antes de subir o cliente."
        )
    
    subscriber = criar_subscriber(settings)
    if subscriber is None:
        raise CustomerBrokerError("nao foi possivel criar subscriber RabbitMQ")
    
    routing_key = routing_localizacao(id_pedido)
    callback = criar_callback_localizacao(id_cliente)

    subscriber.subscribe(EXCHANGE_RASTREIO, routing_key, callback)
    subscriber.subscribe(
        EXCHANGE_PEDIDOS,
        routing_entrega_confirmada(id_pedido),
        criar_callback_entrega_confirmada(id_cliente, subscriber),
    )
    log_apresentacao(
        "cliente",
        f"assinando {EXCHANGE_RASTREIO}/{routing_key} e "
        f"{EXCHANGE_PEDIDOS}/{routing_entrega_confirmada(id_pedido)} para pedido {id_pedido}",
    )
    log_apresentacao(
        f"cliente {id_cliente}",
        f"aguardando entregador (pedido pode ficar na fila se todos estiverem ocupados)",
    )

    try:
        subscriber.start_consuming()
    except KeyboardInterrupt:
        print("[cliente] encerrando assinatura...")
    finally:
        fechar_subscriber(subscriber)


def executar_cliente_broker(
    id_cliente: str,
    id_restaurante: str,
    adm_url: str | None = None,
    id_pedido: UUID | None = None,
    acao: str = "demo",
    broker_settings: BrokerSettings | None = None,
) -> None:
    """
    Run customer flows:
    - criar: only POST /pedidos
    - rastrear: only subscribe to an existing order
    - demo: create order then subscribe
    """
    url_adm = adm_url or os.getenv("ADM_URL", "http://127.0.0.1:8003")

    if acao == "criar":
        pedido_id = criar_pedido_via_adm(url_adm, id_cliente, id_restaurante, id_pedido)
        log_apresentacao("cliente", f"pedido criado: {pedido_id}")
        return
    
    if acao == "rastrear":
        if id_pedido is None:
            raise CustomerBrokerError("--id-pedido e obrigatorio no modo rastrear")
        executar_assinatura_rastreio(id_pedido, id_cliente, broker_settings)
        return
    
    if acao == "demo":
        pedido_id = criar_pedido_via_adm(url_adm, id_cliente, id_restaurante, id_pedido)
        log_apresentacao("cliente", f"pedido criado: {pedido_id}")
        executar_assinatura_rastreio(pedido_id, id_cliente, broker_settings)
        return
    
    raise CustomerBrokerError(f"acao desconhecida: {acao}")
