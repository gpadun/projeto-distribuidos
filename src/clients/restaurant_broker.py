"""Restaurant client that consumes PedidoDisponivel and prepares matching orders."""

import os
import time
from uuid import UUID

import httpx

from src.broker.config import BrokerSettings
from src.broker.factory import criar_subscriber, fechar_subscriber
from src.broker.topology import EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL
from src.clients.driver_broker import parse_pedido_disponivel
from src.core.models import PrepararPedido
from src.core.serialization import to_message_dict
from src.presentation_log import log_apresentacao


class RestaurantBrokerError(RuntimeError):
    """Raised when the restaurant cannot talk to ADM or RabbitMQ."""


def preparar_pedido_via_adm(
    adm_url: str,
    id_restaurante: str,
    id_pedido: UUID,
    timeout: float = 5.0,
) -> dict:
    """Notify the ADM leader that the restaurant prepared the order."""
    requisicao = PrepararPedido(
        idPedido=id_pedido,
        idRestaurante=id_restaurante,
        timestamp=int(time.time()),
    )
    url = f"{adm_url.rstrip('/')}/pedidos/preparar"

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=to_message_dict(requisicao))

    if response.status_code == 200:
        return response.json()

    if response.status_code == 409:
        detail = response.json().get("detail", {})
        lider = detail.get("liderAtual", "?")
        raise RestaurantBrokerError(
            f"ADM em {adm_url} nao e o lider; lider atual: {lider}. "
            "Use a URL do lider em --adm-url."
        )

    raise RestaurantBrokerError(
        f"falha ao preparar pedido: HTTP {response.status_code} - {response.text}"
    )


def criar_callback_pedido_para_restaurante(
    id_restaurante: str,
    adm_url: str,
    preparar_automatico: bool = True,
):
    """Build a PedidoDisponivel callback filtered by restaurant id."""
    preparados: set[UUID] = set()

    def callback(payload: dict) -> None:
        evento = parse_pedido_disponivel(payload)
        if evento.idRestaurante != id_restaurante:
            return

        log_apresentacao(
            f"restaurante {id_restaurante}",
            f"pedido recebido: idPedido={evento.idPedido}",
        )
        if not preparar_automatico or evento.idPedido in preparados:
            return

        preparar_pedido_via_adm(adm_url, id_restaurante, evento.idPedido)
        preparados.add(evento.idPedido)
        log_apresentacao(
            f"restaurante {id_restaurante}",
            f"pedido preparado: idPedido={evento.idPedido}",
        )

    return callback


def executar_restaurante_broker(
    id_restaurante: str,
    adm_url: str | None = None,
    preparar_automatico: bool = True,
    broker_settings: BrokerSettings | None = None,
) -> None:
    """Subscribe to available orders and block until interrupted."""
    settings = broker_settings or BrokerSettings.from_env()
    if not settings.enabled:
        raise RestaurantBrokerError(
            "RabbitMQ desabilitado. Defina RABBITMQ_ENABLED=1 antes de subir o restaurante."
        )

    adm_url = adm_url or os.getenv("ADM_URL", "http://127.0.0.1:8003")
    subscriber = criar_subscriber(settings)
    if subscriber is None:
        raise RestaurantBrokerError("nao foi possivel criar subscriber RabbitMQ")

    subscriber.subscribe(
        EXCHANGE_PEDIDOS,
        ROUTING_PEDIDO_DISPONIVEL,
        criar_callback_pedido_para_restaurante(
            id_restaurante=id_restaurante,
            adm_url=adm_url,
            preparar_automatico=preparar_automatico,
        ),
    )
    print(
        f"[restaurante {id_restaurante}] ouvindo "
        f"{EXCHANGE_PEDIDOS}/{ROUTING_PEDIDO_DISPONIVEL}; ADM={adm_url}"
    )

    try:
        subscriber.start_consuming()
    except KeyboardInterrupt:
        print(f"[restaurante {id_restaurante}] encerrando...")
    finally:
        fechar_subscriber(subscriber)
