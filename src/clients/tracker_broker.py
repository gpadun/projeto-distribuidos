"""Tracker server (R) process that consumes routing and location from RabbitMQ."""

import asyncio
import os
import threading
import time

from src.broker.config import BrokerSettings
from src.broker.factory import criar_publisher, criar_subscriber, fechar_publisher, fechar_subscriber
from src.broker.topology import (
    EXCHANGE_INFRA,
    EXCHANGE_LOCALIZACAO,
    routing_localizacao_para_rastreador,
    routing_roteamento
)
from src.core.models import AtualizacaoRoteamento, LocalizacaoEntregador
from src.servers.tracker_server import TrackerServer


class TrackerBrokerError(RuntimeError):
    """Raised when the tracker process cannot start"""


def _run_async(coro) -> None:
    asyncio.run(coro)


def criar_callback_roteamento(tracker: TrackerServer):
    def callback(payload: dict) -> None:
        atualizacao = AtualizacaoRoteamento.model_validate(payload)
        _run_async(tracker.processar_atualizacao_roteamento(atualizacao))

    return callback

def criar_callback_localizacao(tracker: TrackerServer):
    def callback(payload: dict) -> None:
        localizacao = LocalizacaoEntregador.model_validate(payload)
        _run_async(tracker.processar_localizacao_entregador(localizacao))

    return callback


def executar_rastreador_broker(
    id_servidor: str,
    broker_settings: BrokerSettings | None = None,
) -> None:
    """Run one tracker process with two broker subscriptions."""
    settings = broker_settings or BrokerSettings.from_env()
    if not settings.enabled:
        raise TrackerBrokerError("RABBITMQ_ENABLED=1 e obrigatorio para o rastreador")
    
    publisher = criar_publisher(settings)
    if publisher is None:
        raise TrackerBrokerError("nao foi possivel criar publisher RabbitMQ")
    
    tracker = TrackerServer(id_servidor=id_servidor, publisher=publisher)

    subscriber_roteamento = criar_subscriber(settings)
    subscriber_localizacao = criar_subscriber(settings)
    if subscriber_roteamento is None or subscriber_localizacao is None:
        fechar_publisher(publisher)
        raise TrackerBrokerError("nao foi possivel criar subscribers RabbitMQ")
    
    routing_roteamento_key = routing_roteamento(id_servidor)
    routing_localizacao_key = routing_localizacao_para_rastreador(id_servidor)

    subscriber_roteamento.subscribe(
        EXCHANGE_INFRA,
        routing_roteamento_key,
        criar_callback_roteamento(tracker),
    )
    subscriber_localizacao.subscribe(
        EXCHANGE_LOCALIZACAO,
        routing_localizacao_key,
        criar_callback_localizacao(tracker),
    )

    print(
        f"[rastreador {id_servidor}] ouvindo "
        f"{EXCHANGE_INFRA}/{routing_roteamento_key} e "
        f"{EXCHANGE_LOCALIZACAO}/{routing_localizacao_key}"
    )

    errors: list[Exception] = []

    def consumir(subscriber, rotulo: str) -> None:
        try: 
            subscriber.start_consuming()
        except Exception as exc:
            errors.append(exc)
            print(f"[rastreador {id_servidor}] erro em {rotulo}: {exc}")

    thread_roteamento = threading.Thread(
        target=consumir,
        args=(subscriber_roteamento, "roteamento"),
        daemon=True,
    )
    thread_localizacao = threading.Thread(
        target=consumir,
        args=(subscriber_localizacao, "localizacao"),
        daemon=True,
    )

    thread_roteamento.start()
    thread_localizacao.start()

    try:
        while thread_roteamento.is_alive() and thread_localizacao.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"[rastreador {id_servidor}] encerrando...")
    finally:
        fechar_subscriber(subscriber_roteamento)
        fechar_subscriber(subscriber_localizacao)
        fechar_publisher(publisher)
        thread_roteamento.join(timeout=1)
        thread_localizacao.join(timeout=1)
