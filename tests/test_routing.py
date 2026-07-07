"""Routing tests."""

from uuid import uuid4

import pytest

from src.core.routing import (
    _construir_anel,
    calcular_servidor_responsavel,
    escolher_servidor_consistent_hash,
)


def test_e_deterministico_para_o_mesmo_pedido():
    id_pedido = uuid4()

    resultados = {calcular_servidor_responsavel(id_pedido, 5) for _ in range(100)}

    assert len(resultados) == 1


def test_resultado_esta_sempre_dentro_dos_limites():
    for n_servidores in range(1, 20):
        for _ in range(50):
            indice = calcular_servidor_responsavel(uuid4(), n_servidores)
            assert 0 <= indice < n_servidores


def test_n_servidores_igual_a_um_sempre_retorna_zero():
    assert calcular_servidor_responsavel(uuid4(), 1) == 0


@pytest.mark.parametrize("n_servidores", [0, -1, -10])
def test_n_servidores_invalido_gera_erro(n_servidores):
    with pytest.raises(ValueError):
        calcular_servidor_responsavel(uuid4(), n_servidores)


def test_consistent_hash_retorna_servidor_ativo():
    id_pedido = uuid4()
    servidores = ["R1", "R2", "R3"]

    servidor = escolher_servidor_consistent_hash(id_pedido, servidores)

    assert servidor in servidores


def test_consistent_hash_e_deterministico():
    id_pedido = uuid4()
    servidores = ["R1", "R2", "R3"]

    resultados = {
        escolher_servidor_consistent_hash(id_pedido, servidores)
        for _ in range(20)
    }

    assert len(resultados) == 1


def test_anel_consistent_hash_e_reutilizado_por_cache():
    servidores = ("R1", "R2", "R3")

    _construir_anel.cache_clear()
    _construir_anel(servidores, 32)
    _construir_anel(servidores, 32)

    assert _construir_anel.cache_info().hits == 1
