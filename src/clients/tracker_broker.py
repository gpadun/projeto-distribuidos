"""Tracker server (R) process that consumes routing and location from RabbitMQ."""

import asyncio
import os
import threading
import time
import httpx

from src.broker.config import BrokerSettings
from src.broker.factory import criar_publisher, criar_subscriber, fechar_publisher, fechar_subscriber
from src.broker.topology import (
    EXCHANGE_INFRA,
    EXCHANGE_LOCALIZACAO,
    routing_localizacao_para_rastreador,
    routing_roteamento
)
from src.core.models import AtualizacaoRoteamento, LocalizacaoEntregador, KeepAlive, TipoServidor
from src.core.serialization import to_message_dict
from src.presentation_log import log_apresentacao
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


def _carregar_adm_urls() -> list[str]:
    """Return all ADM base URLs that should receive tracker keepalive."""
    raw = os.getenv("ADM_URLS", "")
    if raw.strip():
        return [url.strip() for url in raw.split(",") if url.strip()]

    fallback = os.getenv("ADM_URL")
    if fallback:
        return [fallback.strip()]

    return [
        "http://127.0.0.1:8001",
        "http://127.0.0.1:8002",
        "http://127.0.0.1:8003",
    ]


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

    adm_urls = _carregar_adm_urls()
    sup_url = os.getenv("SUP_URL")
    intervalo = float(os.getenv("TRACKER_HEARTBEAT_INTERVAL", "5"))

    threading.Thread(
        target=_enviar_keepalive_periodico,
        args=(id_servidor, adm_urls, intervalo),
        daemon=True,
    ).start()

    if sup_url:
        threading.Thread(
            target=_sincronizar_sup_periodico,
            args=(tracker, sup_url, intervalo),
            daemon=True,
        ).start()

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

    log_apresentacao(
        f"rastreador {id_servidor}",
        f"ouvindo {EXCHANGE_INFRA}/{routing_roteamento_key} e "
        f"{EXCHANGE_LOCALIZACAO}/{routing_localizacao_key}; "
        f"keepalive ADMs={', '.join(adm_urls)}",
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


def _enviar_keepalive_periodico(
    id_servidor: str,
    adm_urls: list[str],
    intervalo: float,
) -> None:
    while True:
        mensagem = KeepAlive(
            idServidor=id_servidor,
            tipoServidor=TipoServidor.RASTREADOR,
            timestamp=int(time.time()),
        )
        payload = to_message_dict(mensagem)

        for adm_url in adm_urls:
            try:
                with httpx.Client(timeout=5.0) as client:
                    client.post(
                        f"{adm_url.rstrip('/')}/infra/keepalive",
                        json=payload,
                    )
            except Exception as exc:
                print(
                    f"[rastreador {id_servidor}] erro keepalive em {adm_url}: {exc}"
                )

        time.sleep(intervalo)


def _sincronizar_sup_periodico(tracker: TrackerServer, sup_url: str, intervalo: float) -> None:
    while True:
        try:
            snapshot = tracker.snapshot_rastreios()
            with httpx.Client(timeout=5.0) as client:
                client.post(f"{sup_url.rstrip('/')}/sync", json=snapshot)
        except Exception as exc:
            print(f"[rastreador {tracker.id_servidor}] erro sync SUP: {exc}")
        time.sleep(intervalo)