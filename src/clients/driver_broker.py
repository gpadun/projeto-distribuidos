"""Driver lient that listen to PedidoDisponivel on RabbitMQ."""

import logging
import os
from time import time
from uuid import UUID

import httpx

from src.broker.config import BrokerSettings
from src.broker.factory import criar_subscriber, fechar_subscriber
from src.broker.topology import EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL
from src.core.models import AceitarPedido, PedidoDisponivel
from src.core.serialization import to_message_dict

logger = logging.getLogger(__name__)


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
        timestamp=int(time()),
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


def criar_callback_pedido_disponivel(
    id_entregador: str,
    adm_url: str,
    aceitar_automatico: bool,
):
    """Build the RabbitMQ callback for PedidoDisponivel events."""

    def callback(payload: dict) -> None:
        evento = parse_pedido_disponivel(payload)
        print(
            f"[entregador] pedido disponivel: idPedido={evento.idPedido} "
            f"restaurante={evento.idRestaurante}"
        )

        if not aceitar_automatico:
            return
        
        resultado = aceitar_pedido_via_adm(adm_url, id_entregador, evento.idPedido)
        print(
            f"[entregador] pedido aceito: idPedido={resultado.get('idPedido')} "
            f"rastreador={resultado.get('servidorRastreadorResponsavel')}"
        )

    return callback


def executar_entregador_broker(
        id_entregador: str,
        adm_url: str | None = None,
        aceitar_automatico: bool = True,
        broker_settings: BrokerSettings | None = None,
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
    
    callback = criar_callback_pedido_disponivel(
        id_entregador=id_entregador,
        adm_url=adm_url,
        aceitar_automatico=aceitar_automatico,
    )

    subscriber.subscribe(EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL, callback)
    print(
        f"[entregador] ouvindo {EXCHANGE_PEDIDOS}/{ROUTING_PEDIDO_DISPONIVEL} "
        f"como {id_entregador}; ADM={adm_url}"
    )

    try:
        subscriber.start_consuming()
    except KeyboardInterrupt:
        print("[entregador] encerrando...")
    finally:
        fechar_subscriber(subscriber)
