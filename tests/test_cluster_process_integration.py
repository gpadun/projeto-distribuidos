"""Integration test for the real multi-process ADM validation script."""

import json
import shutil
import socket
import subprocess

import pytest

from src.broker.config import BrokerSettings
from tests.test_broker_integration import rabbitmq_disponivel

pytestmark = pytest.mark.integration


def _porta_em_uso(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", porta)) == 0


def test_validacao_cluster_multiprocesso_real():
    if not rabbitmq_disponivel(
        BrokerSettings(
            host="127.0.0.1",
            port=5672,
            user="dsid",
            password="dsid123",
            enabled=True,
        )
    ):
        pytest.skip("RabbitMQ nao disponivel em 127.0.0.1:5672")

    if shutil.which("powershell") is None:
        pytest.skip("PowerShell nao disponivel para validar processos reais")

    portas = [8001, 8002, 8003, 9101, 9102, 9103]
    portas_em_uso = [porta for porta in portas if _porta_em_uso(porta)]
    if portas_em_uso:
        pytest.skip(f"portas ja em uso: {portas_em_uso}")

    resultado = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts\\validate_cluster_manual.ps1",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )

    assert resultado.returncode == 0, resultado.stderr
    saida = json.loads(resultado.stdout)
    assert saida["liderAntes"] == "adm-3"
    assert saida["restaurantePreparou"] is True
    assert saida["rastreadorDinamicoAtivo"] == "rastreador-3"
    assert "rastreador-3" in saida["rastreadoresAtivosAntesDaFalha"]
    assert saida["liderDepoisDaFalhaAdm3"] == "adm-2"
    assert saida["pedidoConfirmadoNoNovoLider"] == saida["pedidoCriadoNoLider"]
