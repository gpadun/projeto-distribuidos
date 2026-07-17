"""Driver client that listens to PedidoDisponivel on RabbitMQ."""

import os
import time
from uuid import UUID
import asyncio
import random
import threading

import httpx

from src.broker.config import BrokerSettings
from src.broker.factory import criar_subscriber, fechar_subscriber, criar_publisher, fechar_publisher
from src.broker.topology import EXCHANGE_PEDIDOS, ROUTING_PEDIDO_DISPONIVEL, EXCHANGE_LOCALIZACAO, routing_localizacao_para_rastreador
from src.core.models import AceitarPedido, PedidoDisponivel, LocalizacaoEntregador
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


def criar_callback_pedido_disponivel(
    id_entregador: str,
    adm_url: str,
    aceitar_automatico: bool,
    broker_settings: BrokerSettings,
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
        
        thread = threading.Thread(
            target=_publicar_localizacoes_periodicas,
            args=(
                id_entregador,
                evento.idPedido,
                id_rastreador,
                intervalo_gps,
                broker_settings,
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
    
    callback = criar_callback_pedido_disponivel(
        id_entregador=id_entregador,
        adm_url=adm_url,
        aceitar_automatico=aceitar_automatico,
        broker_settings=settings,
        intervalo_gps=intervalo_gps,
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


def _publicar_localizacoes_periodicas(
    id_entregador: str,
    id_pedido: UUID,
    id_rastreador: str,
    intervalo_segundos: float,
    broker_settings: BrokerSettings,
) -> None:
    publisher = criar_publisher(broker_settings)
    if publisher is None:
        return
    
    latitude = -23.55052
    longitude = -46.633308

    try:
        while True:
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
            time.sleep(intervalo_segundos)
    except Exception as exc:
        print(f"[entregador] erro ao publicar localizacao: {exc}")
    finally:
        fechar_publisher(publisher)
